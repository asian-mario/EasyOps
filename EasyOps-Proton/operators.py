import bpy
import bmesh
import gpu
import bgl
import blf
import random
import math
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from bpy_extras import view3d_utils
from bpy.props import EnumProperty, FloatProperty, BoolProperty, IntProperty

from . import utils

"""
    TODO: Consider splitting operators.py, getting too large

    Oh my god, please consider a refactor.
"""

class OBJECT_OT_easy_random_materials(bpy.types.Operator):
    """Assign Random Materials to Selected Objects"""
    bl_idname = "object.assign_random_materials"
    bl_label = "Assign Random Materials"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        description="Randomization mode",
        items=[
            ('BASIC', "Basic", "Random colors"),
            ('METALLIC', "Metallic", "Greyscale metallic"),
        ],
        default='BASIC'
    )

    @staticmethod
    def assign_viewport_display_color(mat, color):
        mat.diffuse_color = (*color, 1.0)

    def execute(self, context):
        targets = utils.get_target_objects(context)
        if not targets:
            self.report({'WARNING'}, "No mesh objects found")
            return {'CANCELLED'}

        for obj in targets:
            if obj.type == 'MESH':
                mat = bpy.data.materials.new("RandomMaterial")
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get("Principled BSDF")

                if self.mode == 'BASIC':
                    col = [random.random() for _ in range(3)]
                    metallic = 0.0
                else:
                    grey = random.uniform(
                        context.scene.easy_utils_props.metallic_color_min,
                        context.scene.easy_utils_props.metallic_color_max
                    )
                    col = [grey] * 3
                    metallic = 1.0

                bsdf.inputs["Base Color"].default_value = (*col, 1.0)
                bsdf.inputs["Metallic"].default_value = metallic

                obj.data.materials.clear()
                obj.data.materials.append(mat)
                self.assign_viewport_display_color(mat, col)

        self.report({'INFO'}, f"Random materials ({self.mode}) assigned.")
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class OBJECT_OT_easy_shade_smooth(bpy.types.Operator):
    """Shade Smooth + optional Auto Smooth"""
    bl_idname = "object.easy_shade_smooth"
    bl_label = "Shade Smooth"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.easy_utils_props
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH':
                obj.select_set(True)
                context.view_layer.objects.active = obj
                bpy.ops.object.shade_smooth()
                """
                Deprecated:
                if props.enable_auto_smooth:
                    mod = obj.modifiers.new(name="SmoothByAngle", type = 'NORMALS_SMOOTH')
                    mod.mode = 'FACE_AREA'
                    mod.angle = math.radians(self.auto_smooth_angle) 
                """
                obj.select_set(False)
        self.report({'INFO'}, "Shade Smooth complete.")
        return {'FINISHED'}


class OBJECT_OT_easy_smart_uv_unwrap(bpy.types.Operator):
    """Smart UV Unwrap with adjustable margin"""
    bl_idname = "object.easy_smart_uv_unwrap"
    bl_label = "Smart UV Unwrap"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        margin = context.scene.easy_utils_props.island_margin
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH':
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.uv.smart_project(island_margin=margin)
                bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, f"Unwrapped with margin {margin:.3f}")
        return {'FINISHED'}


class OBJECT_OT_easy_auto_rename(bpy.types.Operator):
    """Auto-rename mesh objects & their data"""
    bl_idname = "object.easy_auto_rename"
    bl_label = "Auto Rename"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        prefix = context.scene.easy_utils_props.rename_prefix
        targets = sorted(utils.get_target_objects(context),
                         key=lambda o: o.location.z, reverse=True)
        count = 1
        for obj in targets:
            if obj.type == 'MESH':
                obj.name = f"{prefix}{count}"
                obj.data.name = f"{prefix}{count}"
                count += 1
        self.report({'INFO'}, "Renaming complete.")
        return {'FINISHED'}


class OBJECT_OT_easy_remove_doubles(bpy.types.Operator):
    """Merge verts by distance on meshes"""
    bl_idname = "object.easy_remove_doubles"
    bl_label = "Remove Doubles"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH':
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles()
                bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "Remove Doubles done")
        return {'FINISHED'}


class OBJECT_OT_easy_clean_geometry(bpy.types.Operator):
    """Clean loose & degenerate geometry"""
    bl_idname = "object.easy_clean_geometry"
    bl_label = "Clean Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH':
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles()
                bpy.ops.mesh.delete_loose()
                bpy.ops.mesh.dissolve_degenerate()
                bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "Geometry cleaned.")
        return {'FINISHED'}


class OBJECT_OT_easy_bevel(bpy.types.Operator):
    """Add a Bevel modifier"""
    bl_idname = "object.easy_bevel"
    bl_label = "Bevel"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and not any(m.type=='BEVEL' for m in obj.modifiers):
                mod = obj.modifiers.new("Bevel", 'BEVEL')
                mod.width = 0.02
                mod.segments = 3
                mod.profile = 0.7
        self.report({'INFO'}, "Bevel modifier added.")
        return {'FINISHED'}


class OBJECT_OT_easy_boolean_difference(bpy.types.Operator):
    """Boolean Difference"""
    bl_idname = "object.easy_boolean_difference"
    bl_label = "Boolean Difference"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.view_layer.objects.active
        modified_objects = []

        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Difference", 'BOOLEAN')
                mod.operation = 'DIFFERENCE'
                mod.object = active
                modified_objects.append(obj)
        
        utils.recalculate_normals_for_objects(context, modified_objects)
        utils.turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Difference applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_boolean_union(bpy.types.Operator):
    """Boolean Union"""
    bl_idname = "object.easy_boolean_union"
    bl_label = "Boolean Union"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.view_layer.objects.active
        modified_objects = []
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Union", 'BOOLEAN')
                mod.operation = 'UNION'
                mod.object = active
                modified_objects.append(obj)

        utils.recalculate_normals_for_objects(context, modified_objects)
        utils.turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Union applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_boolean_intersect(bpy.types.Operator):
    """Boolean Intersect"""
    bl_idname = "object.easy_boolean_intersect"
    bl_label = "Boolean Intersect"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        active = context.view_layer.objects.active
        modified_objects = []
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Intersect", 'BOOLEAN')
                mod.operation = 'INTERSECT'
                mod.object = active
                modified_objects.append(obj)

        utils.recalculate_normals_for_objects(context, modified_objects)
        utils.turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Intersect applied.")
        return {'FINISHED'}

class OBJECT_OT_easy_boolean_slice(bpy.types.Operator):
    """Slice Boolean"""
    bl_idname = "object.easy_boolean_slice"
    bl_label = "Boolean Slice"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        active = context.view_layer.objects.active
        targets = [obj for obj in context.selected_objects if obj != active and obj.type == 'MESH']

        if not targets:
            self.report({'WARNING'}, "No valid target objects selected.")
            return {'CANCELLED'}

        for target in targets:
            target_copy = target.copy()
            target_copy.data = target.data.copy()
            target_copy.name = target.name + "_Slice"
            context.collection.objects.link(target_copy)

            diff_mod = target.modifiers.new("Slice_Difference", "BOOLEAN")
            diff_mod.operation = 'DIFFERENCE'
            diff_mod.object = active

            intersect_mod = target_copy.modifiers.new("Slice_Intersect", "BOOLEAN")
            intersect_mod.operation = 'INTERSECT'
            intersect_mod.object = active

        utils.recalculate_normals_for_objects(context, targets)
            
        utils.turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Slice applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_smart_apply(bpy.types.Operator):
    """Apply only valid boolean modifiers, remove dead ones"""
    bl_idname = "object.easy_smart_apply"
    bl_label = "Smart Apply"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0
        applied_count = 0

        for obj in utils.get_target_objects(context):
            if obj.type != 'MESH':
                continue

            # Remove dead modifiers
            for mod in list(obj.modifiers):
                if mod.type == 'BOOLEAN':
                    if not mod.object or mod.object.name not in bpy.data.objects:
                        obj.modifiers.remove(mod)
                        removed_count += 1

            # Apply remaining boolean modifiers
            for mod in list(obj.modifiers):
                if mod.type == 'BOOLEAN' and mod.object and mod.object.name in bpy.data.objects:
                    context.view_layer.objects.active = obj
                    bpy.ops.object.modifier_apply(modifier=mod.name)
                    applied_count += 1

        self.report({'INFO'}, f"Applied {applied_count} boolean(s), removed {removed_count} dead modifier(s).")
        return {'FINISHED'}


class OBJECT_OT_easy_smart_decimate(bpy.types.Operator):
    """Add Decimate modifier"""
    bl_idname = "object.easy_smart_decimate"
    bl_label = "Smart Decimate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and not any(m.type=='DECIMATE' for m in obj.modifiers):
                mod = obj.modifiers.new("Decimate", 'DECIMATE')
                mod.ratio = 0.5
        self.report({'INFO'}, "Decimate modifier added.")
        return {'FINISHED'}


class OBJECT_OT_easy_sharpen_edges(bpy.types.Operator):
    """Sharpen edges operator"""
    bl_label = "Sharpen Edges"
    bl_idname = "object.easy_sharpen_edges"
    bl_description = "Marks selected edges as sharp / equivalent to flat shading."
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        target_objects = utils.get_target_objects(context)
        for obj in target_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.mark_sharp()
                bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "Sharp edges marked on selected/all objects.")
        return {'FINISHED'}


class OBJECT_OT_easy_ssharpen(bpy.types.Operator):
    """Smart Sharpen: detect, bevel & auto-smooth"""
    bl_idname = "object.easy_ssharpen"
    bl_label = "SSharpen"
    bl_options = {'REGISTER', 'UNDO'}

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply all modifiers before sharpening",
        default=True
    )

    sharpness_angle: FloatProperty(
        name="Sharpness Angle", 
        description="Angle threshold for edge detection",
        default=math.radians(30),
        min=math.radians(1),
        max=math.radians(180),
        unit='ROTATION'
    )

    bevel_width: FloatProperty(
        name="Bevel Width",
        description="Width of the bevel modifier", 
        default=0.02,
        min=0.001,
        max=1.0
    )

    bevel_segments: IntProperty(
        name="Bevel Segments",
        description="Number of bevel segments",
        default=3,
        min=1,
        max=12
    )

    # AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA THIS STINKS IT ALL STINKS WHY WHY WHY! DOES THE DEBUGGER NOT WORK AT ALL
    # I CANT GET NOTING DONE BECAUSE EVERYTIME I MAKE A MISTAKE I HAVE TO LOAD IT IN BLENDER AND THEN UNLOAD IT WHICH TAKES
    # GODDAMN AGES AND THE EXTENSION DOESNT WORK YOU STINK

    def execute(self, context):
        processed_count = 0

        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH':
                context.view_layer.objects.active = obj

                if self.apply_modifiers:
                    self.smart_apply_modifiers(obj)
                    utils.recalculate_normals_for_objects(context, [obj])

                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_mode(type='EDGE')
                bpy.ops.mesh.select_all(action='SELECT')

                bpy.ops.mesh.mark_sharp(clear=True)

                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.mesh.edges_select_sharp(sharpness=self.sharpness_angle)
                bpy.ops.mesh.mark_sharp()

                bpy.ops.object.mode_set(mode='OBJECT')

                if not any(mod.type == 'BEVEL' for mod in obj.modifiers):
                    bevel_mod = obj.modifiers.new("SSharpen_Bevel", 'BEVEL')
                    bevel_mod.limit_method = 'ANGLE'
                    bevel_mod.angle_limit = self.sharpness_angle
                    bevel_mod.width = self.bevel_width
                    bevel_mod.segments = self.bevel_segments
                    bevel_mod.profile = 0.7
                
                bpy.ops.object.shade_smooth()

                processed_count += 1
        
        self.report({'INFO'}, f"SSharpen applied to {processed_count} objects.")
        return {'FINISHED'}

    def smart_apply_modifiers(self, obj):
        if not obj.modifiers:
            return

        priority_order = {
            'BOOLEAN': 1,      
            'MIRROR': 2,     
            'ARRAY': 3,       
            'SOLIDIFY': 4,    
            # 'BEVEL': 5,    LOL ARE U FKN STUPID?    
            'REMESH': 5,     
            'DECIMATE': 6,    
            'SUBSURF': 7,     
        }

        priority_mods = []
        other_mods = []

        for mod in obj.modifiers:
            if mod.type in priority_order:
                priority_mods.append((priority_order[mod.type], mod))
            else:
                other_mods.append(mod)
        
        priority_mods.sort(key=lambda x: x[0])

        for _, mod in priority_mods:
            if mod.type == 'BOOLEAN' and (not mod.object or mod.object.name not in bpy.data.objects):
                obj.modifiers.remove(mod)
                continue
            
            try:
                bpy.ops.object.modifier_apply(modifier=mod.name)
            except:
                if mod.name in obj.modifiers:
                    obj.modifiers.remove(mod)

        for mod in other_mods:
            try:
                if mod.type != 'BEVEL':
                    bpy.ops.object.modifier_apply(modifier=mod.name)
            except:
                if mod.name in obj.modifiers:
                    obj.modifiers.remove(mod)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)


class OBJECT_OT_easy_quad_remesh(bpy.types.Operator):
    """Quad remesh"""
    bl_idname = "object.easy_quad_remesh"
    bl_label = "Quad Remesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and not any(m.type=='REMESH' for m in obj.modifiers):
                mod = obj.modifiers.new("QuadRemesh", 'REMESH')
                mod.mode = 'SHARP' 
                mod.octree_depth = 5
                mod.scale = 0.9
                mod.sharpness = 1.0
                mod.use_remove_disconnected = False
        self.report({'INFO'}, "Quad Remesh modifier added.")
        return {'FINISHED'}


class OBJECT_OT_easy_mirror(bpy.types.Operator):
    """Smart mirror with axis detection + clipping"""
    bl_idname = "object.easy_mirror"
    bl_label = "Smart Mirror"
    bl_options = {'REGISTER', 'UNDO'}

    axis: EnumProperty(
        name="Mirror Axis",
        description="Axis to mirror across",
        items=[
            ('AUTO', "Auto", "Detect axis automatically based on object bounds"),
            ('X', "X", "Mirror across X axis"),
            ('Y', "Y", "Mirror across Y axis"),     
            ('Z', "Z", "Mirror across Z axis"),
            ('XY', "XY", "Mirror across X and Y axes"),
            ('XZ', "XZ", "Mirror across X and Z axes"),
            ('YZ', "YZ", "Mirror across Y and Z axes"),
            ('XYZ', "XYZ", "Mirror across all axes"),
        ],
        default='AUTO'
    )

    use_clip: BoolProperty(
        name="Use Clipping",
        description="Prevent vertices from crossing the mirror plane",
        default=True
    )

    use_merge: BoolProperty(
        name="Use Merge",
        description="Merge vertices at the mirror plane of the object",
        default=True
    )

    merge_threshold: FloatProperty(
        name="Merge Threshold",
        description="Distance threshold when merging vertices",
        default=0.001,
        min=0.0,   
        max=1.0,
        precision=4
    )

    use_bisect: BoolProperty(
        name="Bisect",
        description="Cut the mesh along the mirror plane",
        default=True
    )

    clear_existing: BoolProperty(
        name="Clear Existing Mirrors",
        description="Remove existing mirror modifiers",
        default=True
    )

    def get_auto_axis(self, obj):
        if not obj or obj.type != 'MESH':
            return 'X'
        
        bbox = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        
        min_x = min(corner.x for corner in bbox)
        max_x = max(corner.x for corner in bbox)
        min_y = min(corner.y for corner in bbox)
        max_y = max(corner.y for corner in bbox)
        min_z = min(corner.z for corner in bbox)
        max_z = max(corner.z for corner in bbox)

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2

        offsets = {
            'X': abs(center_x),
            'Y': abs(center_y),
            'Z': abs(center_z),
        }
        return min(offsets, key=offsets.get)

    def add_mirror_modifier(self, obj, axis_name, use_x=False, use_y=False, use_z=False):
        """Mirror modifier with specified settigs"""
        mod_name = f"Mirror_{axis_name}"

        if self.clear_existing:
            existing = obj.modifiers.get(mod_name)
            if existing:
                obj.modifiers.remove(existing)
        
        if not self.clear_existing and any(m.type == 'MIRROR' and m.use_axis[0] == use_x and m_use_axis[1] == use_y and m.use_axis[2] == use_z for m in obj.modifiers):
            return False
        
        mirror_mod = obj.modifiers.new(name=mod_name, type='MIRROR')
        mirror_mod.use_axis = (use_x, use_y, use_z)
        mirror_mod.use_clip = self.use_clip
        mirror_mod.use_bisect_axis = (
            self.use_bisect and use_x, 
            self.use_bisect and use_y, 
            self.use_bisect and use_z
        )

        if self.use_merge:
            mirror_mod.merge_threshold = self.merge_threshold
        
        return True
    
    def execute(self, context):
        targets = utils.get_target_objects(context)
        if not targets:
            self.report({'WARNING'}, "No mesh objects found")
            return {'CANCELLED'}
        
        processed_count = 0
        for obj in targets:
            if obj.type != 'MESH':
                continue
            
            if self.clear_existing:
                for mod in list(obj.modifiers):
                    if mod.type == 'MIRROR':
                        obj.modifiers.remove(mod)
            
            if self.axis == 'AUTO':
                auto_axis = self.get_auto_axis(obj)
                axes_to_mirror = [auto_axis]
            elif self.axis in ['X', 'Y', 'Z']:
                axes_to_mirror = [self.axis]
            else:
                axes_to_mirror = list(self.axis)

            added_any = False
            for axis_char in axes_to_mirror:
                use_x = axis_char == 'X'
                use_y = axis_char == 'Y'
                use_z = axis_char == 'Z'
                if self.add_mirror_modifier(obj, axis_char, use_x, use_y, use_z):
                    added_any = True
                
            if added_any:
                processed_count += 1
            
        if processed_count == 0:
            self.report({'INFO'}, "No new mirror modifiers added (already exist or no valid objects).")
        else:
            axis_text = self.axis if self.axis != 'AUTO' else f"Auto ({self.get_auto_axis(targets[0]) if targets else 'X'})"
            self.report({'INFO'}, f"Mirror modifier ({axis_text}) added to {processed_count} object(s).")

        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "axis")
        layout.separator()

        col = layout.column()
        col.prop(self, "use_clip")
        col.prop(self, "use_merge")

        if self.use_merge:
            col.prop(self, "merge_threshold")
        col.prop(self, "use_bisect")
        layout.separator()
        col.prop(self, "clear_existing")
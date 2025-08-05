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
            ('X', "X", "Mirror across X axis"),
            ('Y', "Y", "Mirror across Y axis"),     
            ('Z', "Z", "Mirror across Z axis"),
            ('XY', "XY", "Mirror across X and Y axes"),
            ('XZ', "XZ", "Mirror across X and Z axes"),
            ('YZ', "YZ", "Mirror across Y and Z axes"),
            ('XYZ', "XYZ", "Mirror across all axes"),
        ],
        default='X'
    )

    flip_x: BoolProperty(
        name="Flip X Axis",
        description="Flip the X axis when mirroring",
        default=False
    )

    flip_y: BoolProperty(
        name="Flip Y Axis",
        description="Flip the Y axis when mirroring",
        default=False
    )

    flip_z: BoolProperty(
        name="Flip Z Axis",
        description="Flip the Z axis when mirroring",
        default=False
    )

    use_gizmo: BoolProperty(
        name="Use Viewport Gizmo",
        description="Use the mirror gizmo for axis selection",
        default=True
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

        if use_x and self.flip_x:
            mirror_mod.use_axis = (True, use_y, use_z)
            mirror_mod.offset_u = -1.0
        if use_y and self.flip_y:
            mirror_mod.use_axis = (use_x, True, use_z)
            mirror_mod.offset_v = -1.0
        if use_z and self.flip_z:
            mirror_mod.use_axis = (use_x, use_y, True)

        if self.use_merge:
            mirror_mod.merge_threshold = self.merge_threshold
        
        return True
    
    def execute(self, context):
        targets = utils.get_target_objects(context)
        if not targets:
            self.report({'WARNING'}, "No mesh objects found")
            return {'CANCELLED'}
        
        if self.use_gizmo:
            return self.invoke_gizmo_mode(context)
        
        processed_count = 0
        for obj in targets:
            if obj.type != 'MESH':
                continue
            
            if self.clear_existing:
                for mod in list(obj.modifiers):
                    if mod.type == 'MIRROR':
                        obj.modifiers.remove(mod)
            
            if self.axis in ['X', 'Y', 'Z']:
                axes_to_mirror = [self.axis]
            else:
                axes_to_mirror = list(self.axis)

            added_any = False
            for axis_char in axes_to_mirror:
                use_x = axis_char == 'X'
                use_y = axis_char == 'Y'
                use_z = axis_char == 'Z'

                flip_x = use_x and self.flip_x
                flip_y = use_y and self.flip_y
                flip_z = use_z and self.flip_z
                if self.add_mirror_modifier(obj, axis_char, use_x, use_y, use_z, flip_x, flip_y, flip_z):
                    added_any = True
                
            if added_any:
                processed_count += 1
            
        if processed_count == 0:
            self.report({'INFO'}, "No new mirror modifiers added (already exist or no valid objects).")
        else:
            flip_info = []
            if self.flip_x: flip_info.append("X-flipped")
            if self.flip_y: flip_info.append("Y-flipped")
            if self.flip_z: flip_info.append("Z-flipped")
            flip_text = f" (Flipped: {', '.join(flip_info)})" if flip_info else ""
            self.report({'INFO'}, f"Mirror modifier ({self.axis}{flip_text}) added to {processed_count} object(s).")

        return {'FINISHED'}
    
    def invoke_gizmo_mode(self, context):
        bpy.ops.object.easy_mirror_gizmo('INVOKE_DEFAULT', use_clip=self.use_clip, use_merge=self.use_merge, merge_threshold=self.merge_threshold, use_bisect=self.use_bisect, clear_existing=self.clear_existing)
        return {'RUNNING_MODAL'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "axis")
        layout.prop(self, "use_gizmo")

        if not self.use_gizmo:
            row = layout.row()
            if 'X' in self.axis:
                row.prop(self, "flip_x", toggle=True)
            if 'Y' in self.axis:
                row.prop(self, "flip_y", toggle=True)
            if 'Z' in self.axis:
                row.prop(self, "flip_z", toggle=True)

        layout.separator()

        col = layout.column()
        col.prop(self, "use_clip")
        col.prop(self, "use_merge")

        if self.use_merge:
            col.prop(self, "merge_threshold")
        col.prop(self, "use_bisect")
        layout.separator()
        col.prop(self, "clear_existing")

# im working on this okay just let it be
class OBJECT_OT_easy_mirror_gizmo(bpy.types.Operator):
    """Mirror Gizmo Operator"""
    bl_idname = "object.easy_mirror_gizmo"
    bl_label = "Mirror Gizmo"
    bl_options = {'REGISTER', 'UNDO'}

    use_clip: BoolProperty(default=True)
    use_merge: BoolProperty(default=True)
    merge_threshold: FloatProperty(default=0.001)
    use_bisect: BoolProperty(default=True)
    clear_existing: BoolProperty(default=True)

    selected_axis = None
    selected_flip = False
    def modal(self, context, event):
        context.area.tag_redraw()

        if event.type == {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        
        if event.type == 'MOUSEMOVE':
            self.update_hover(context, event)
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            axis, flip = self.get_clicked_axis(context, event)
            if axis:
                self.apply_mirror(context, axis, flip)
                self.cleanup_gizmo(context)
                return {'FINISHED'}
        
        if event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cleanup_gizmo(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}
    
    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            self._handle = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_gizmo, (context,), 'WINDOW', 'POST_PIXEL'
            )
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, "Click on axis arrow to mirror. Right-click or ESC to cancel.")
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

    def cleanup_gizmo(self, context):
        if hasattr(self, '_handle'):
            bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
            del self._handle
        context.area.tag_redraw()

    def update_hover(self, context, event):
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y

        targets = utils.get_target_objects(context)
        if not targets:
            self.selected_axis = None
            self.selected_flip = False
            return
        
        obj = targets[0]
        world_pos = obj.matrix_world.translation

        region = context.region
        rv3d = context.region_data
        screen_pos = view3d_utils.location_3d_to_region_2d(region, rv3d, world_pos)

        if not screen_pos:
            self.selected_axis = None
            self.selected_flip = False
            return
        
        arrow_length = 60
        arrow_width = 20

        def point_in_arrow(mouse_pos, start_pos, end_pos, width):
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            length = math.sqrt(dx*dx + dy*dy)
            if length == 0:
                return False
            
            dx /= length
            dy /= length

            mx = mouse_pos[0] - start_pos[0]
            my = mouse_pos[1] - start_pos[1]

            dot = mx * dx + my * dy
            if dot < 0 or dot > length:
                return False
            
            perp_dist = abs(mx * (-dy)  + my * dx)
            return perp_dist < width
        
        mouse_pos = (mouse_x, mouse_y)

        x_pos_end = (screen_pos[0] + arrow_length, screen_pos[1])
        x_neg_end = (screen_pos[0] - arrow_length, screen_pos[1])
        z_pos_end = (screen_pos[0], screen_pos[1] + arrow_length)
        z_neg_end = (screen_pos[0], screen_pos[1] - arrow_length)
        
        y_pos_end = (screen_pos[0] + arrow_length * 0.7, screen_pos[1] + arrow_length * 0.7)
        y_neg_end = (screen_pos[0] - arrow_length * 0.7, screen_pos[1] - arrow_length * 0.7)

        # i am so sorry for this code
        if point_in_arrow(mouse_pos, screen_pos, x_pos_end, arrow_width):
            self.selected_axis = 'X'
            self.selected_flip = False
        elif point_in_arrow(mouse_pos, screen_pos, x_neg_end, arrow_width):
            self.selected_axis = 'X'
            self.selected_flip = True
        elif point_in_arrow(mouse_pos, screen_pos, y_pos_end, arrow_width):
            self.selected_axis = 'Y'
            self.selected_flip = False
        elif point_in_arrow(mouse_pos, screen_pos, y_neg_end, arrow_width):
            self.selected_axis = 'Y'
            self.selected_flip = True
        elif point_in_arrow(mouse_pos, screen_pos, z_pos_end, arrow_width): 
            self.selected_axis = 'Z'
            self.selected_flip = False
        elif point_in_arrow(mouse_pos, screen_pos, z_neg_end, arrow_width):
            self.selected_axis = 'Z'
            self.selected_flip = True
        else:
            self.selected_axis = None
            self.selected_flip = False

    def get_clicked_axis(self, context, event):
        mouse_x = event.mouse_region_x
        mouse_y = event.mouse_region_y
        
        targets = utils.get_target_objects(context)
        if not targets:
            return None, False

        obj = targets[0]
        world_pos = obj.matrix_world.translation

        region = context.region
        rv3d = context.region_data
        screen_pos = view3d_utils.location_3d_to_region_2d(region, rv3d, world_pos)

        if not screen_pos:
            return None, False
        
        arrow_length = 60   
        arrow_width = 20

        x_pos_end = (screen_pos[0] + arrow_length, screen_pos[1])
        x_neg_end = (screen_pos[0] - arrow_length, screen_pos[1])
        
        z_pos_end = (screen_pos[0], screen_pos[1] + arrow_length)
        z_neg_end = (screen_pos[0], screen_pos[1] - arrow_length)
        
        y_pos_end = (screen_pos[0] + arrow_length * 0.7, screen_pos[1] + arrow_length * 0.7)
        y_neg_end = (screen_pos[0] - arrow_length * 0.7, screen_pos[1] - arrow_length * 0.7)
        
        def point_in_arrow(mouse_pos, start_pos, end_pos, width):
            dx = end_pos[0] - start_pos[0]
            dy = end_pos[1] - start_pos[1]
            length = math.sqrt(dx*dx + dy*dy)
            if length == 0:
                return False
            
            dx /= length
            dy /= length

            mx = mouse_pos[0] - start_pos[0]  
            my = mouse_pos[1] - start_pos[1]
            
            dot = mx * dx + my * dy
            if dot < 0 or dot > length:
                return False
                
            perp_dist = abs(mx * (-dy) + my * dx)
            return perp_dist < width
        
        mouse_pos = (mouse_x, mouse_y)
        
        if point_in_arrow(mouse_pos, screen_pos, x_pos_end, arrow_width):
            return 'X', False
        if point_in_arrow(mouse_pos, screen_pos, y_pos_end, arrow_width):
            return 'Y', False  
        if point_in_arrow(mouse_pos, screen_pos, z_pos_end, arrow_width):
            return 'Z', False
            
        if point_in_arrow(mouse_pos, screen_pos, x_neg_end, arrow_width):
            return 'X', True
        if point_in_arrow(mouse_pos, screen_pos, y_neg_end, arrow_width):
            return 'Y', True
        if point_in_arrow(mouse_pos, screen_pos, z_neg_end, arrow_width):
            return 'Z', True
            
        return None, False

    def apply_mirror(self, context, axis, flip):
        targets = utils.get_target_objects(context)
        processed_count = 0

        for obj in targets:
            if obj.type != 'MESH':
                continue
            
            if self.clear_existing:
                for mod in list(obj.modifiers):
                    if mod.type == 'MIRROR':
                        obj.modifiers.remove(mod)
            
            mod_name = f"Mirror_{axis}{'_Flipped' if flip else ''}"
            mirror_mod = obj.modifiers.new(mod_name, 'MIRROR')

            use_x = axis == 'X'
            use_y = axis == 'Y'
            use_z = axis == 'Z'
            mirror_mod.use_axis = (use_x, use_y, use_z)

            mirror_mod.use_clip = self.use_clip
            mirror_mod.use_bisect_axis = (
                self.use_bisect and use_x,
                self.use_bisect and use_y,
                self.use_bisect and use_z
            )

            if flip:
                if axis == 'X':
                    empty = bpy.data.objects.new(f"Mirror_Origin{axis}", None)
                    empty.location= obj.location.copy()
                    empty.location.x = -empty.location.x
                    context.collection.objects.link(empty)
                    mirror_mod.mirror_object = empty
                
            if self.use_merge:
                mirror_mod.merge_threshold = self.merge_threshold

            processed_count += 1
        
        flip_text = " (flipped)" if flip else ""
        self.report({'INFO'}, f"Mirror {axis}{flip_text} applied to {processed_count} object(s)")

    def draw_gizmo(self, context):
        targets = utils.get_target_objects(context)
        if not targets:
            return
            
        obj = targets[0]
        world_pos = obj.matrix_world.translation
        
        region = context.region
        rv3d = context.region_data
        screen_pos = view3d_utils.location_3d_to_region_2d(region, rv3d, world_pos)
        
        if not screen_pos:
            return

        gpu.state.blend_set('ALPHA')

        center_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        center_batch = batch_for_shader(center_shader, 'POINTS', {"pos": [(screen_pos[0], screen_pos[1])]})
        center_shader.bind()
        center_shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
        center_batch.draw(center_shader)

        arrow_length = 60
        line_width = 3
        
        # this stinks
        self.draw_arrow(screen_pos, (screen_pos[0] + arrow_length, screen_pos[1]), (1.0, 0.0, 0.0, 0.8), line_width)
        self.draw_arrow(screen_pos, (screen_pos[0] - arrow_length, screen_pos[1]), (0.8, 0.0, 0.0, 0.6), line_width)
        self.draw_arrow(screen_pos, (screen_pos[0], screen_pos[1] + arrow_length), (0.0, 0.0, 1.0, 0.8), line_width)
        self.draw_arrow(screen_pos, (screen_pos[0], screen_pos[1] - arrow_length), (0.0, 0.0, 0.8, 0.6), line_width)
        self.draw_arrow(screen_pos, (screen_pos[0] + arrow_length * 0.7, screen_pos[1] + arrow_length * 0.7), (0.0, 1.0, 0.0, 0.8), line_width)
        self.draw_arrow(screen_pos, (screen_pos[0] - arrow_length * 0.7, screen_pos[1] - arrow_length * 0.7), (0.0, 0.8, 0.0, 0.6), line_width)

        self.draw_text(screen_pos[0] + arrow_length + 10, screen_pos[1], "X+", (1.0, 0.0, 0.0, 1.0))
        self.draw_text(screen_pos[0] - arrow_length - 20, screen_pos[1], "X-", (0.8, 0.0, 0.0, 1.0))
        self.draw_text(screen_pos[0], screen_pos[1] + arrow_length + 10, "Z+", (0.0, 0.0, 1.0, 1.0))
        self.draw_text(screen_pos[0], screen_pos[1] - arrow_length - 20, "Z-", (0.0, 0.0, 0.8, 1.0))
        self.draw_text(screen_pos[0] + arrow_length * 0.7 + 10, screen_pos[1] + arrow_length * 0.7, "Y+", (0.0, 1.0, 0.0, 1.0))
        self.draw_text(screen_pos[0] - arrow_length * 0.7 - 20, screen_pos[1] - arrow_length * 0.7, "Y-", (0.0, 0.8, 0.0, 1.0))
        
        gpu.state.blend_set('NONE')
    
    def draw_arrow(self, start_pos, end_pos, color, width):
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        batch = batch_for_shader(shader, 'LINES', {"pos": [start_pos, end_pos]})
        shader.bind()
        shader.uniform_float("color", color)
        gpu.state.line_width_set(width)
        batch.draw(shader)

        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            dx /= length
            dy /= length
            
            head_size = 8
            p1 = (end_pos[0] - head_size * dx + head_size * 0.5 * dy,
                  end_pos[1] - head_size * dy - head_size * 0.5 * dx)
            p2 = (end_pos[0] - head_size * dx - head_size * 0.5 * dy,
                  end_pos[1] - head_size * dy + head_size * 0.5 * dx)
            
            head_batch = batch_for_shader(shader, 'TRIS', 
                                        {"pos": [end_pos, p1, p2]})
            head_batch.draw(shader)
    
    def draw_text(self, x, y, text, color):
        """Draw text at screen coordinates"""
        font_id = 0
        blf.position(font_id, x, y, 0)
        blf.size(font_id, 12)
        blf.color(font_id, *color)
        blf.draw(font_id, text)
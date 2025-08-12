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
                    utils.smart_apply_modifiers(obj)
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
        """Mirror modifier with bisect + flip support (Blender 4.5)"""
        mod_name = f"Mirror_{axis_name}"

        # 1. Remove existing modifier if requested
        if self.clear_existing:
            existing = obj.modifiers.get(mod_name)
            if existing:
                obj.modifiers.remove(existing)

        # 2. Skip creation if an identical mirror exists (and no flips are active)
        if not self.clear_existing:
            for m in obj.modifiers:
                if (
                    m.type == 'MIRROR'
                    and tuple(m.use_axis) == (use_x, use_y, use_z)
                    and not (self.flip_x or self.flip_y or self.flip_z)
                ):
                    return False

        # 3. Create & configure the mirror modifier
        mirror_mod = obj.modifiers.new(name=mod_name, type='MIRROR')
        mirror_mod.use_axis = (use_x, use_y, use_z)
        mirror_mod.use_clip = self.use_clip

        # 4. Bisect plane + Flip options
        mirror_mod.use_bisect_axis = (
            self.use_bisect and use_x,
            self.use_bisect and use_y,
            self.use_bisect and use_z,
        )
        mirror_mod.use_bisect_flip_axis = (
            self.flip_x and self.use_bisect and use_x,
            self.flip_y and self.use_bisect and use_y,
            self.flip_z and self.use_bisect and use_z,
        )

        # 5. Assign a mirror_object when flipping
        if use_x and self.flip_x:
            empty = bpy.data.objects.new(f"{obj.name}_MirrorFlipX", None)
            empty.location = obj.location.copy()
            empty.location.x *= -1
            bpy.context.collection.objects.link(empty)
            mirror_mod.mirror_object = empty

        if use_y and self.flip_y:
            empty = bpy.data.objects.new(f"{obj.name}_MirrorFlipY", None)
            empty.location = obj.location.copy()
            empty.location.y *= -1
            bpy.context.collection.objects.link(empty)
            mirror_mod.mirror_object = empty

        if use_z and self.flip_z:
            empty = bpy.data.objects.new(f"{obj.name}_MirrorFlipZ", None)
            empty.location = obj.location.copy()
            empty.location.z *= -1
            bpy.context.collection.objects.link(empty)
            mirror_mod.mirror_object = empty

        # 6. Merge threshold (if requested)
        if self.use_merge:
            mirror_mod.use_mirror_merge = True
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
                if self.add_mirror_modifier(obj, axis_char, use_x, use_y, use_z):
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

        gizmo_world_size = self.calculate_gizmo_world_size(context, world_pos)

        arrow_endpoints = self.calculate_arrow_endpoints_world(obj, gizmo_world_size)
        screen_endpoints = {}

        center_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, world_pos)

        if not center_screen:
            self.selected_axis = None
            self.selected_flip = False
            return

        for axis_dir, world_end in arrow_endpoints.items():
            screen_end = view3d_utils.location_3d_to_region_2d(region, rv3d, world_end)
            if screen_end:
                screen_endpoints[axis_dir] = screen_end

        mouse_pos = (mouse_x, mouse_y)
        arrow_width = 20

        for axis_dir, screen_end in screen_endpoints.items():
            if self.point_in_arrow(mouse_pos, center_screen, screen_end, arrow_width):
                if axis_dir.endswith('_pos'):
                    self.selected_axis = axis_dir[0]
                    self.selected_flip = False
                else:
                    self.selected_axis = axis_dir[0]
                    self.selected_flip = True
        
        self.selected_axis = None
        self.selected_flip = False
    
    def calculate_gizmo_world_size(self, context, world_pos):
        rv3d = context.region_data

        if rv3d.view_perspective == 'ORTHO':
            return rv3d.view_distance * 0.3
        else:
            view_matrix = rv3d.view_matrix
            camera_pos = view_matrix.inverted().translation
            distance = (world_pos - camera_pos).length
            
            return distance * 0.3

    def calculate_arrow_endpoints_world(self, obj, gizmo_size):
        world_pos = obj.matrix_world.translation

        obj_matrix = obj.matrix_world.to_3x3().normalized()
        local_x = obj_matrix @ Vector((1, 0, 0))
        local_y = obj_matrix @ Vector((0, 1, 0))
        local_z = obj_matrix @ Vector((0, 0, 1))

        endpoints = {
            'X_pos': world_pos + local_x * gizmo_size,
            'X_neg': world_pos - local_x * gizmo_size,
            'Y_pos': world_pos + local_y * gizmo_size,
            'Y_neg': world_pos - local_y * gizmo_size,
            'Z_pos': world_pos + local_z * gizmo_size,
            'Z_neg': world_pos - local_z * gizmo_size,
        }

        return endpoints
    
    def point_in_arrow(self, mouse_pos, start_pos, end_pos, width):
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

        gizmo_world_size = self.calculate_gizmo_world_size(context, world_pos)
        arrow_endpoints = self.calculate_arrow_endpoints_world(obj, gizmo_world_size)
        center_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, world_pos)
        if not center_screen: 
            return None, False

        mouse_pos = (mouse_x, mouse_y)
        arrow_width = 20

        for axis_dir, world_end in arrow_endpoints.items():
            screen_end = view3d_utils.location_3d_to_region_2d(region, rv3d, world_end)
            if screen_end and self.point_in_arrow(mouse_pos, center_screen, screen_end, arrow_width):
                axis = axis_dir[0]
                flip = axis_dir.endswith('_neg')
                return axis, flip
        
        return None, False

    def apply_mirror(self, context, axis, flip):
        targets = utils.get_target_objects(context)
        processed_count = 0

        for obj in targets:
            if obj.type != 'MESH':
                continue

            if self.clear_existing:
                for m in list(obj.modifiers):
                    if m.type == 'MIRROR':
                        obj.modifiers.remove(m)

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
                self.use_bisect and use_z,
            )
            mirror_mod.use_bisect_flip_axis = (
                flip and self.use_bisect and use_x,
                flip and self.use_bisect and use_y,
                flip and self.use_bisect and use_z,
            )

            if flip:
                empty = bpy.data.objects.new(f"{obj.name}_Mirror{axis}", None)
                empty.location = obj.location.copy()
                if use_x: empty.location.x *= -1
                if use_y: empty.location.y *= -1
                if use_z: empty.location.z *= -1
                context.collection.objects.link(empty)
                mirror_mod.mirror_object = empty

            # merge at plane
            if self.use_merge:
                mirror_mod.use_mirror_merge = True
                mirror_mod.merge_threshold = self.merge_threshold

            processed_count += 1

        self.report(
            {'INFO'},
            f"Mirror {axis}{' (flipped)' if flip else ''} applied to {processed_count} object(s)"
        )


    def draw_gizmo(self, context):
        targets = utils.get_target_objects(context)
        if not targets:
            return

        gpu.state.depth_test_set('NONE')
        
        obj = targets[0]
        world_pos = obj.matrix_world.translation
        
        region = context.region
        rv3d = context.region_data
        center_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, world_pos)
        
        if not center_screen:
            return

        gpu.state.blend_set('ALPHA')

        center_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        center_batch = batch_for_shader(center_shader, 'POINTS', {"pos": [(center_screen[0], center_screen[1])]})
        center_shader.bind()
        center_shader.uniform_float("color", (1.0, 1.0, 1.0, 1.0))
        center_batch.draw(center_shader)

        gizmo_world_size = self.calculate_gizmo_world_size(context, world_pos)
        arrow_endpoints = self.calculate_arrow_endpoints_world(obj, gizmo_world_size)
        line_width = 3
        
        axis_config = {
            'X_pos': {'color': (1.0, 0.0, 0.0, 0.8), 'label': 'X+', 'offset': (10, 0)},
            'X_neg': {'color': (0.8, 0.0, 0.0, 0.6), 'label': 'X-', 'offset': (-20, 0)},
            'Y_pos': {'color': (0.0, 1.0, 0.0, 0.8), 'label': 'Y+', 'offset': (10, 10)},
            'Y_neg': {'color': (0.0, 0.8, 0.0, 0.6), 'label': 'Y-', 'offset': (-20, -20)},
            'Z_pos': {'color': (0.0, 0.0, 1.0, 0.8), 'label': 'Z+', 'offset': (0, 10)},
            'Z_neg': {'color': (0.0, 0.0, 0.8, 0.6), 'label': 'Z-', 'offset': (0, -20)},
        }

        for axis_dir, world_end in arrow_endpoints.items():
            screen_end = view3d_utils.location_3d_to_region_2d(region, rv3d, world_end)
            if screen_end:
                config = axis_config[axis_dir]

                color = config['color']
                if self.selected_axis and axis_dir.startswith(self.selected_axis):
                    if (axis_dir.endswith('_pos') and not self.selected_flip) or \
                        (axis_dir.endswith('_neg') and self.selected_flip):
                        color = (color[0], color[1], color[2], 1.0)
                
                self.draw_arrow(center_screen, screen_end, color, line_width)

                label_x = screen_end[0] + config['offset'][0]
                label_y = screen_end[1] + config['offset'][1]
                self.draw_text(label_x, label_y, config['label'], color)

        gpu.state.blend_set('NONE')
        gpu.state.depth_test_set('LESS_EQUAL')
    
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

class OBJECT_OT_easy_edge_wear(bpy.types.Operator):
    bl_idname = "object.easy_edge_wear"
    bl_label = "Edge Wear"
    bl_options = {'REGISTER', 'UNDO'}

    wear_intensity: FloatProperty(
        name="Wear Intensity",
        description="Intensity of edge wear",
        default = 0.1,
        min=0.001,
        max=1.0,
        precision=3
    )

    wear_scale: FloatProperty(
        name="Wear Scale",
        description="Scale of the wear pattern",
        default=5.0,
        min=0.1,
        max=50.0,
        precision=2
    )

    edge_threshold: FloatProperty(
        name="Edge Detection Angle",
        description="Angle threshold for detecting sharp edges",
        default=math.radians(45),
        min=math.radians(1),
        max=math.radians(180),
        unit='ROTATION'
    )

    wear_falloff: FloatProperty(
        name="Wear Falloff",
        description="Distance the wear extends from the edges",
        default=0.05,
        min=0.001,
        max=1.0,
        precision=3
    )
    wear_randomness: FloatProperty(
        name="Randomness",
        description="Randomness in wear pattern",
        default=0.5,
        min=0.0,
        max=1.0,
        precision=2
    )
    
    wear_type: EnumProperty(
        name="Wear Type",
        description="Type of wear pattern to generate",
        items=[
            ('SCRATCH', "Scratches", "Generate scratch-like wear patterns"),
            ('CHIPS', "Chips", "Generate chipped edge patterns"),
            ('SMOOTH', "Smooth Wear", "Generate smooth worn edges"),
            ('MIXED', "Mixed", "Combination of wear types"),
        ],
        default='MIXED'
    )
    
    subdivision_levels: IntProperty(
        name="Detail Level",
        description="Subdivision levels for wear detail",
        default=2,
        min=1,
        max=4
    )
    
    apply_modifiers: BoolProperty(
        name="Apply Existing Modifiers",
        description="Apply existing modifiers before adding wear",
        default=True
    )
    
    preserve_sharp_edges: BoolProperty(
        name="Preserve Sharp Edges",
        description="Keep original sharp edge marking",
        default=True
    )
    
    seed: IntProperty(
        name="Random Seed",
        description="Seed for randomization",
        default=0,
        min=0,
        max=999999
    )

    def execute(self, context):
        random.seed(self.seed)
        processed_count = 0

        for obj in utils.get_target_objects(context):
            if obj.type != 'MESH':
                continue

            context.view_layer.objects.active = obj
            if self.apply_modifiers:
                utils.smart_apply_modifiers(obj)

            self.remove_existing_wear_modifiers(context, obj)
            self.generate_edge_wear(context, obj)

            utils.recalculate_normals_for_objects(context, [obj])
            processed_count += 1
        
        self.report({'INFO'}, f"Edge wear applied to {processed_count} object(s).")
        return {'FINISHED'}
    
    def remove_existing_wear_modifiers(self, context, obj):
        mods_to_remove = []
        for mod in obj.modifiers:
            if mod.name.startswith("EdgeWear_"):
                mods_to_remove.append(mod)
        
        for mod in mods_to_remove:
            obj.modifiers.remove(mod)

    def generate_edge_wear(self, context, obj):
        
        if self.has_geometry_nodes_support():
            self.add_geometry_nodes_wear(obj)
        else:
            self.add_displacement_wear(obj)

        if self.subdivision_levels > 0:
            subsurf = obj.modifiers.new("EdgeWear_Subsurf", 'SUBSURF')
            subsurf.levels = min(self.subdivision_levels, 2)
        
        if self.wear_type in ['SMOOTH', 'MIXED']:
            smooth_mod = obj.modifiers.new("EdgeWear_Smooth", 'SMOOTH')
            smooth_mod.iterations = 2
            smooth_mod.factor = 0.2
    
    def has_geometry_nodes_support(self):
        return bpy.app.version >= (3, 0, 0)

    def add_geometry_nodes_wear(self, obj):
        geo_mod = obj.modifiers.new("EdgeWear_Geometry", 'NODES')
        node_group = self.create_edge_wear_node_group()
        geo_mod.node_group = node_group

        try:
            geo_mod["Input_2"] = self.wear_intensity
            geo_mod["Input_3"] = self.wear_scale
            geo_mod["Input_4"] = self.wear_falloff
            geo_mod["Input_5"] = self.wear_randomness
            geo_mod["Input_6"] = self.edge_threshold
        except (KeyError, TypeError):
            for input_socket in geo_mod.node_group.interface.items_tree:
                if hasattr(input_socket, 'socket_type') and input_socket.socket_type == 'NodeSocketFloat':
                    if "Intensity" in input_socket.name:
                        try:
                            geo_mod[input_socket.identifier] = self.wear_intensity
                        except:
                            pass
                    elif "Scale" in input_socket.name:
                        try:
                            geo_mod[input_socket.identifier] = self.wear_scale
                        except:
                            pass
                    elif "Falloff" in input_socket.name:
                        try:
                            geo_mod[input_socket.identifier] = self.wear_falloff
                        except:
                            pass
                    elif "Randomness" in input_socket.name:
                        try:
                            geo_mod[input_socket.identifier] = self.wear_randomness
                        except:
                            pass
                    elif "Edge Angle" in input_socket.name:
                        try:
                            geo_mod[input_socket.identifier] = self.edge_threshold
                        except:
                            pass
        if "EdgeWear_Edges" in obj.vertex_groups:
            pass

    def create_edge_wear_node_group(self):

        """
            this was beyond unholy to do and unholy to test if this works first try I will rip out my toenail out of glee
        """
        group_name = "EdgeWear_NodeGroup"
        if group_name in bpy.data.node_groups:
            return bpy.data.node_groups[group_name]
        
        node_group = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
        
        group_input = node_group.nodes.new('NodeGroupInput')
        group_output = node_group.nodes.new('NodeGroupOutput')
        group_input.location = (-800, 0)
        group_output.location = (800, 0)
        
        # Create input/output sockets
        node_group.interface.new_socket(name="Geometry", socket_type='NodeSocketGeometry', in_out='INPUT')
        node_group.interface.new_socket(name="Intensity", socket_type='NodeSocketFloat', in_out='INPUT')
        node_group.interface.new_socket(name="Scale", socket_type='NodeSocketFloat', in_out='INPUT')
        node_group.interface.new_socket(name="Falloff", socket_type='NodeSocketFloat', in_out='INPUT')
        node_group.interface.new_socket(name="Randomness", socket_type='NodeSocketFloat', in_out='INPUT')
        node_group.interface.new_socket(name="Edge Angle", socket_type='NodeSocketFloat', in_out='INPUT')
        
        node_group.interface.new_socket(name="Geometry", socket_type='NodeSocketGeometry', in_out='OUTPUT')
        
        # Set default values
        node_group.interface.items_tree["Intensity"].default_value = 0.1
        node_group.interface.items_tree["Scale"].default_value = 5.0
        node_group.interface.items_tree["Falloff"].default_value = 0.05
        node_group.interface.items_tree["Randomness"].default_value = 0.5
        node_group.interface.items_tree["Edge Angle"].default_value = math.radians(45)
        
        nodes = node_group.nodes
        links = node_group.links

        edge_angle = nodes.new('GeometryNodeInputMeshEdgeAngle')
        edge_angle.location = (-600, 200)

        compare = nodes.new('FunctionNodeCompare')
        compare.location = (-400, 200)
        compare.data_type = 'FLOAT'
        compare.operation = 'GREATER_THAN'
        
        position = nodes.new('GeometryNodeInputPosition')
        position.location = (-600, -100)
        
        vector_scale = nodes.new('ShaderNodeVectorMath')
        vector_scale.location = (-500, -100)
        vector_scale.operation = 'MULTIPLY'

        noise_texture = nodes.new('ShaderNodeTexNoise')
        noise_texture.location = (-400, -100)
        noise_texture.noise_dimensions = '3D'

        voronoi = nodes.new('ShaderNodeTexVoronoi')
        voronoi.location = (-400, -300)
        voronoi.voronoi_dimensions = '3D'
        voronoi.feature = 'F1'

        wave = nodes.new('ShaderNodeTexWave')
        wave.location = (-400, -400)
        wave.wave_type = 'BANDS'
        wave.wave_profile = 'SAW'
        
        mix_wear_types = nodes.new('ShaderNodeMix')
        mix_wear_types.location = (-100, -300)
        mix_wear_types.data_type = 'FLOAT'
        mix_wear_types.blend_type = 'MIX'

        random_value = nodes.new('FunctionNodeRandomValue')
        random_value.location = (-400, -200)
        random_value.data_type = 'FLOAT'

        vector_to_float = nodes.new('ShaderNodeSeparateXYZ')
        vector_to_float.location = (-500, -200)
        
        add_xyz = nodes.new('ShaderNodeMath')
        add_xyz.location = (-450, -150)
        add_xyz.operation = 'ADD'
        
        add_z = nodes.new('ShaderNodeMath') 
        add_z.location = (-400, -150)
        add_z.operation = 'ADD'
        
        color_ramp = nodes.new('ShaderNodeValToRGB')
        color_ramp.location = (0, -300)
        color_ramp.color_ramp.elements[0].position = 0.3
        color_ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
        color_ramp.color_ramp.elements[1].position = 0.7
        color_ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
        
        multiply_intensity = nodes.new('ShaderNodeMath')
        multiply_intensity.location = (-200, -100)
        multiply_intensity.operation = 'MULTIPLY'

        multiply_edge_noise = nodes.new('ShaderNodeMath')
        multiply_edge_noise.location = (0, 0)
        multiply_edge_noise.operation = 'MULTIPLY'
        

        normal = nodes.new('GeometryNodeInputNormal')
        normal.location = (0, -200)
        
        displacement_vector = nodes.new('ShaderNodeVectorMath')
        displacement_vector.location = (200, -100)
        displacement_vector.operation = 'MULTIPLY'
        
        negate_displacement = nodes.new('ShaderNodeMath')
        negate_displacement.location = (300, -200)
        negate_displacement.operation = 'MULTIPLY'
        negate_displacement.inputs[1].default_value = -1.0
        final_intensity = nodes.new('ShaderNodeMath')
        final_intensity.location = (400, -100)
        final_intensity.operation = 'MULTIPLY'
        
        set_position = nodes.new('GeometryNodeSetPosition')
        set_position.location = (600, 0)

        links.new(group_input.outputs["Geometry"], set_position.inputs["Geometry"])
        links.new(set_position.outputs["Geometry"], group_output.inputs["Geometry"])

        links.new(edge_angle.outputs["Unsigned Angle"], compare.inputs[0])
        links.new(group_input.outputs["Edge Angle"], compare.inputs[1])

        links.new(position.outputs["Position"], vector_scale.inputs[0])
        links.new(group_input.outputs["Scale"], vector_scale.inputs[1])

        links.new(vector_scale.outputs["Vector"], noise_texture.inputs["Vector"])
        links.new(group_input.outputs["Scale"], noise_texture.inputs["Scale"])
        
        links.new(vector_scale.outputs["Vector"], voronoi.inputs["Vector"])
        links.new(group_input.outputs["Scale"], voronoi.inputs["Scale"])
        
        links.new(vector_scale.outputs["Vector"], wave.inputs["Vector"])
        links.new(group_input.outputs["Scale"], wave.inputs["Scale"])

        links.new(position.outputs["Position"], vector_to_float.inputs["Vector"])
        links.new(vector_to_float.outputs["X"], add_xyz.inputs[0])
        links.new(vector_to_float.outputs["Y"], add_xyz.inputs[1])
        links.new(add_xyz.outputs["Value"], add_z.inputs[0])
        links.new(vector_to_float.outputs["Z"], add_z.inputs[1])
        links.new(add_z.outputs["Value"], random_value.inputs["ID"])

        links.new(noise_texture.outputs["Fac"], mix_wear_types.inputs["A"])
        links.new(voronoi.outputs["Distance"], mix_wear_types.inputs["B"])
        links.new(group_input.outputs["Randomness"], mix_wear_types.inputs["Factor"])
        links.new(mix_wear_types.outputs["Result"], color_ramp.inputs["Fac"])
        
        links.new(color_ramp.outputs["Color"], multiply_intensity.inputs[0])
        links.new(group_input.outputs["Intensity"], multiply_intensity.inputs[1])
        
        links.new(compare.outputs["Result"], multiply_edge_noise.inputs[0])
        links.new(multiply_intensity.outputs["Value"], multiply_edge_noise.inputs[1])
        links.new(multiply_edge_noise.outputs["Value"], negate_displacement.inputs[0])
        links.new(negate_displacement.outputs["Value"], final_intensity.inputs[0])
        links.new(group_input.outputs["Falloff"], final_intensity.inputs[1])
    
        links.new(normal.outputs["Normal"], displacement_vector.inputs[0])
        links.new(final_intensity.outputs["Value"], displacement_vector.inputs[1])
        links.new(displacement_vector.outputs["Vector"], set_position.inputs["Offset"])
        
        return node_group


    def add_displacement_wear(self, obj):
        edge_group = self.create_edge_vertex_group(obj)

        displace_mod = obj.modifiers.new("EdgeWear_Displace", 'DISPLACE')
        displace_mod.vertex_group = edge_group.name
        displace_mod.strength = -self.wear_intensity
        displace_mod.direction = 'NORMAL'

        wear_texture = self.create_wear_texture()
        if wear_texture:
            displace_mod.texture = wear_texture

        if self.wear_type in ['SCRATCH', 'MIXED']:
            wave_mod = obj.modifiers.new("EdgeWear_Wave", 'WAVE')
            wave_mod.vertex_group = edge_group.name
            wave_mod.height = self.wear_intensity * 0.5
            wave_mod.width = 1.0
            wave_mod.speed = 0
            wave_mod.speed = random.random() * 6.28 #hehehe

        smooth_mod = obj.modifiers.new("EdgeWear_CorrectiveSmooth", 'CORRECTIVE_SMOOTH')
        smooth_mod.iterations = 3
        smooth_mod.smooth_type = 'LENGTH_WEIGHTED'
    
    def create_edge_vertex_group(self, obj):
        group_name = "EdgeWear_Edges"
        if group_name in obj.vertex_groups:
            obj.vertex_groups.remove(obj.vertex_groups[group_name])
        
        edge_group = obj.vertex_groups.new(name=group_name)

        original_active = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj

        angle_degrees = math.degrees(self.edge_threshold)
        original_mode = bpy.context.mode

        try:
            bpy.ops.object.mode_set(mode='EDIT')
            bm = bmesh.from_edit_mesh(obj.data)
            bm.edges.ensure_lookup_table()
            bm.faces.ensure_lookup_table()
            bm.verts.ensure_lookup_table()

            for v in bm.verts:
                v.select = False
            for e in bm.edges:
                e.select = False
            for f in bm.faces:
                f.select = False

            edge_verts = set()
            thresh = self.edge_threshold

            for edge in bm.edges:
                add_edge = False
                # this is going to be similar to detect_sharp_edges but i need to modify it a little so i wont be calling it
                if edge.is_manifold and len(edge.link_faces) == 2:
                    angle = edge.link_faces[0].normal.angle(edge.link_faces[1].normal)
                    if angle > thresh:
                        add_edge = True
                elif len(edge.link_faces) == 1:
                    add_edge = True

                if add_edge:
                    edge_verts.update([v.index for v in edge.verts])

            if self.wear_falloff > 0:
                extended_verts = set(edge_verts)
                for vert_idx in list(edge_verts):
                    vert = bm.verts[vert_idx]
                    for edge in vert.link_edges:
                        for connected_vert in edge.verts:
                            if connected_vert.index not in extended_verts:
                                dist = (vert.co - connected_vert.co).length
                                if dist <= self.wear_falloff:
                                    weight = 1.0 - (dist / self.wear_falloff)

                                    if random.random() < weight * (1.0 - self.wear_randomness * 0.5):
                                        extended_verts.add(connected_vert.index)
                
                edge_verts = extended_verts

            bmesh.update_edit_mesh(obj.data)
            bpy.ops.object.mode_set(mode='OBJECT')

            for vert_idx in edge_verts:
                base_weight = 1.0
                if self.wear_randomness > 0:
                    weight_variation = self.wear_randomness * random.random()
                    base_weight = max(0.1, 1.0 - weight_variation)

                edge_group.add([vert_idx], base_weight, 'REPLACE')
        
        finally:
            bpy.context.view_layer.objects.active = original_active
            if original_mode != 'OBJECT':
                try:
                    bpy.ops.object.mode_set(mode=original_mode.replace('_', '').lower())
                except:
                    pass
        
        return edge_group

    def create_wear_texture(self):
        texture_name = f"EdgeWear_Texture_{self.seed}"

        if texture_name in bpy.data.textures:
            bpy.data.textures.remove(bpy.data.textures[texture_name])

        wear_texture = bpy.data.textures.new(texture_name, 'NOISE')
        
        try:
            wear_texture.noise_scale = self.wear_scale
        except AttributeError:
            if hasattr(wear_texture, 'scale'):
                wear_texture.scale = self.wear_scale
            else:
                print(f"Warning: Could not set noise scale for texture {texture_name}")
        try:
            if self.wear_type == 'SCRATCH':
                wear_texture.noise_basis = 'BLENDER_ORIGINAL'
                wear_texture.noise_type = 'HARD_NOISE'
            elif self.wear_type == 'CHIPS':
                wear_texture.noise_basis = 'VORONOI_CRACKLE'
                wear_texture.noise_type = 'HARD_NOISE'
            elif self.wear_type == 'SMOOTH':
                wear_texture.noise_basis = 'IMPROVED_PERLIN'
                wear_texture.noise_type = 'SOFT_NOISE'
            else:  
                wear_texture.noise_basis = 'BLENDER_ORIGINAL'
                wear_texture.noise_type = 'SOFT_NOISE'
        except AttributeError as e:
            print(f"Warning: Could not set noise properties: {e}")
            try:
                wear_texture.noise_basis = 'PERLIN_ORIGINAL'
                wear_texture.noise_type = 'SOFT_NOISE'
            except:
                pass

        return wear_texture
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        layout = self.layout

        col = layout.column()
        col.prop(self, "wear_type")
        col.prop(self, "wear_intensity")
        col.prop(self, "wear_falloff")
        col.prop(self, "wear_randomness")

        layout.separator()

        col = layout.column()
        col.label(text="Edge Detection:")
        col.prop(self, "edge_threshold")

        layout.separator()
        col = layout.column()
        col.prop(self, "apply_modifiers")
        col.prop(self, "preserve_sharp_edges")
        col.prop(self, "seed")
    
class OBJECT_OT_easy_edge_wear_regenerate(bpy.types.Operator):
    bl_idname = "object.easy_edge_wear_regenerate"
    bl_label = "Regenerate Edge Wear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        new_seed = random.randint(0, 999999)

        bpy.ops.object.easy_edge_wear(
            'INVOKE_DEFAULT',
            seed=new_seed
        )

        return {'FINISHED'}

class OBJECT_OT_easy_edge_wear_remove(bpy.types.Operator):
    bl_idname = "object.easy_edge_wear_remove"
    bl_label = "Remove Edge Wear"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        removed_count = 0

        for obj in utils.get_target_objects(context):
            if obj.type != 'MESH':
                continue

            mods_to_remove = []
            for mod in obj.modifiers:
                if mod.name.startswith("EdgeWear_"):
                    mods_to_remove.append(mod)
                    removed_count += 1
        
            groups_to_remove = []
            for group in obj.vertex_groups:
                if group.name.startswith("EdgeWear_"):
                    groups_to_remove.append(group)
            
            for group in groups_to_remove:
                obj.vertex_groups.remove(group)

            textures_to_remove = []
            for texture in bpy.data.textures:
                if texture.name.startswith("EdgeWear_Texture_"):
                    texture_users = sum(1 for obj_check in bpy.data.objects
                                        if obj_check.type == 'MESH'
                                        for mod in obj_check.modifiers
                                        if hasattr(mod, 'texture') and mod.texture == texture)

                    if texture_users <= 1:
                        textures_to_remove.append(texture)
            
            for texture in textures_to_remove:
                bpy.data.textures.remove(texture)

        self.report({'INFO'}, f"Removed edge wear from objects ({removed_count} modifiers removed)")
        return {'FINISHED'}
                                    
                            
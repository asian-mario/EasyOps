import bpy
import bmesh
import gpu
import bgl
import random
import math
from gpu_extras.batch import batch_for_shader
from mathutils import Vector, Matrix
from bpy_extras import view3d_utils
from bpy.props import EnumProperty, FloatProperty, BoolProperty

from . import utils


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
                if props.enable_auto_smooth:
                    obj.data.use_auto_smooth = True
                    obj.data.auto_smooth_angle = math.radians(props.auto_smooth_angle)
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
                bpy.ops.mesh.merge_by_distance()
                bpy.ops.object.mode_set(mode='OBJECT')
        self.report({'INFO'}, "Merge by distance done.")
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
                bpy.ops.mesh.merge_by_distance()
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
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Difference", 'BOOLEAN')
                mod.operation = 'DIFFERENCE'
                mod.object = active
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
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Union", 'BOOLEAN')
                mod.operation = 'UNION'
                mod.object = active
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
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Intersect", 'BOOLEAN')
                mod.operation = 'INTERSECT'
                mod.object = active
        utils.turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Intersect applied.")
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

    def execute(self, context):
        for obj in utils.get_target_objects(context):
            if obj.type == 'MESH':
                utils.detect_sharp_edges(obj)
                utils.apply_bevel_modifier(obj)
                utils.enable_auto_smooth(obj)
        self.report({'INFO'}, "SSharpen complete.")
        return {'FINISHED'}

# Freeform drawing
class OBJECT_OT_easy_freeform_boolean(bpy.types.Operator):
    """Draw freeform boolean shapes in the viewport"""
    bl_idname = "object.easy_freeform_boolean"
    bl_label = "FreeForm Boolean"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    
    # Properties
    operation: EnumProperty(
        name="Boolean Operation",
        description="Type of boolean operation to perform",
        items=[
            ('DIFFERENCE', "Difference", "Subtract the drawn shape"),
            ('UNION', "Union", "Add the drawn shape"),
            ('INTERSECT', "Intersect", "Keep only intersection"),
        ],
        default='DIFFERENCE'
    )
    
    extrude_depth: FloatProperty(
        name="Extrude Depth",
        description="How deep to extrude the drawn shape",
        default=1.0,
        min=0.01,
        max=10.0
    )
    
    both_directions: BoolProperty(
        name="Both Directions",
        description="Extrude in both directions from the drawing plane",
        default=True
    )
    
    def invoke(self, context, event):
        # Initialize instance variables here instead of in __init__
        self.points = []
        self.mouse_pos = Vector((0, 0))
        self.drawing = False
        self.draw_handler = None
        self.target_objects = []
        self.preview_mesh = None
        
        if context.area.type == 'VIEW_3D':
            # Get target objects
            self.target_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not self.target_objects:
                self.report({'WARNING'}, "No mesh objects selected")
                return {'CANCELLED'}
            
            # Set up drawing
            self.points = []
            self.drawing = True
            
            # Add viewport drawing handler
            args = (self, context)
            self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL'
            )
            
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, f"FreeForm Boolean ({self.operation}) - Click to add points, Enter to finish, Esc to cancel")
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        
        if event.type == 'MOUSEMOVE':
            return {'RUNNING_MODAL'}
        
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            # Add point to polygon
            self.add_point(context, event)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RET' and event.value == 'PRESS':
            # Finish drawing and create boolean
            if len(self.points) >= 3:
                self.create_boolean_mesh(context)
                self.cleanup(context)
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "Need at least 3 points to create a shape")
                return {'RUNNING_MODAL'}
        
        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            # Cancel operation
            self.cleanup(context)
            return {'CANCELLED'}
        
        elif event.type == 'Z' and event.value == 'PRESS':
            # Undo last point
            if self.points:
                self.points.pop()
            return {'RUNNING_MODAL'}
        
        return {'RUNNING_MODAL'}
    
    def add_point(self, context, event):
        """Convert mouse position to 3D world coordinate"""
        region = context.region
        rv3d = context.region_data
        
        # Get mouse coordinate in region
        coord = Vector((event.mouse_region_x, event.mouse_region_y))
        
        # Convert to 3D world coordinate on active object plane or XY plane
        if context.active_object and context.active_object.type == 'MESH':
            # Use active object's location as the drawing plane
            depth_location = context.active_object.location
        else:
            depth_location = Vector((0, 0, 0))
        
        # Cast ray from mouse to get 3D coordinate
        world_pos = view3d_utils.region_2d_to_location_3d(
            region, rv3d, coord, depth_location
        )
        
        self.points.append(world_pos)
    
    def create_boolean_mesh(self, context):
        """Create the boolean mesh from drawn points"""
        if len(self.points) < 3:
            return
        
        # Create new mesh
        mesh = bpy.data.meshes.new("FreeFormBoolean")
        obj = bpy.data.objects.new("FreeFormBoolean", mesh)
        
        # Create bmesh
        bm = bmesh.new()
        
        # Add vertices from points
        verts = [bm.verts.new(pt) for pt in self.points]

        # Create and store the face, then ensure lookup
        face = bm.faces.new(verts)
        bm.faces.ensure_lookup_table()

        # Extrude outwards/inwards from that face
        if self.both_directions:
            # forward extrusion
            extrude1 = bmesh.ops.extrude_face_region(bm, geom=[face])
            verts1  = [e for e in extrude1['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm,
                                vec=(0, 0, self.extrude_depth/2),
                                verts=verts1)

            # reverse extrusion
            extrude2 = bmesh.ops.extrude_face_region(bm, geom=[face])
            verts2  = [e for e in extrude2['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm,
                                vec=(0, 0, -self.extrude_depth/2),
                                verts=verts2)
        else:
            extrude = bmesh.ops.extrude_face_region(bm, geom=[face])
            verts_extruded = [e for e in extrude['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm,
                                vec=(0, 0, self.extrude_depth),
                                verts=verts_extruded)

                
        # Update mesh
        bm.to_mesh(mesh)
        bm.free()
        
        # Add to scene
        context.collection.objects.link(obj)
        
        # Apply boolean to target objects
        for target in self.target_objects:
            if target.type == 'MESH':
                mod = target.modifiers.new("FreeForm Boolean", 'BOOLEAN')
                mod.operation = self.operation
                mod.object = obj
        
        # Turn boolean object into wireframe and move to cuts collection
        from . import utils
        utils.turn_into_wireframe(obj)
        
        self.report({'INFO'}, f"FreeForm Boolean ({self.operation}) created with {len(self.points)} points")
    
    def draw_callback_px(self, op, context):
        """Draw the polygon in the viewport"""
        if not self.drawing:
            return
        
        # Enable blending for transparency
        bgl.glEnable(bgl.GL_BLEND)
        bgl.glBlendFunc(bgl.GL_SRC_ALPHA, bgl.GL_ONE_MINUS_SRC_ALPHA)
        
        # Draw points
        if self.points:
            # Convert 3D points to 2D screen coordinates
            region = context.region
            rv3d = context.region_data
            
            screen_points = []
            for point in self.points:
                screen_coord = view3d_utils.location_3d_to_region_2d(region, rv3d, point)
                if screen_coord:
                    screen_points.append(screen_coord)
            
            if len(screen_points) >= 2:
                # Draw lines connecting points
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                
                # Create line batch
                coords = []
                for i in range(len(screen_points)):
                    coords.append(screen_points[i])
                    if i < len(screen_points) - 1:
                        coords.append(screen_points[i + 1])
                
                # Add line from last point to mouse (preview)
                if screen_points:
                    coords.append(screen_points[-1])
                    coords.append(self.mouse_pos)
                
                batch = batch_for_shader(shader, 'LINES', {"pos": coords})
                
                # Set color based on operation
                if self.operation == 'DIFFERENCE':
                    color = (1.0, 0.2, 0.2, 0.8)  # Red
                elif self.operation == 'UNION':
                    color = (0.2, 1.0, 0.2, 0.8)  # Green
                else:  # INTERSECT
                    color = (0.2, 0.2, 1.0, 0.8)  # Blue
                
                shader.bind()
                shader.uniform_float("color", color)
                batch.draw(shader)
            
            # Draw points as circles
            for screen_point in screen_points:
                self.draw_circle(screen_point, 4, (1.0, 1.0, 1.0, 1.0))
        
        # Restore OpenGL defaults
        bgl.glDisable(bgl.GL_BLEND)
    
    def draw_circle(self, center, radius, color):
        """Draw a simple circle at screen coordinates"""
        import math
        
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        
        # Generate circle vertices
        segments = 16
        coords = []
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            coords.append((x, y))
        
        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
    
    def cleanup(self, context):
        """Clean up the drawing handler"""
        if self.draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None
        
        self.drawing = False
        context.area.tag_redraw()
    
    def draw(self, context):
        """Draw the operator properties in the dialog"""
        layout = self.layout
        layout.prop(self, "operation")
        layout.prop(self, "extrude_depth")
        layout.prop(self, "both_directions")
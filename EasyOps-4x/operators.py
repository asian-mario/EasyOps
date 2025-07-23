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
    """Draw freeform boolean shapes in the viewport with real-time preview"""
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
        # Initialize instance variables
        self.points = []
        self.mouse_pos = Vector((0, 0))
        self.drawing = False
        self.adjusting_depth = False
        self.draw_handler = None
        self.target_objects = []
        self.preview_mesh = None
        self.initial_mouse_y = 0
        self.initial_depth = 1.0
        self.current_depth = 1.0
        self.drawing_plane_normal = Vector((0, 0, 1))
        self.drawing_plane_center = Vector((0, 0, 0))
        self.preview_batch = None
        self.preview_shader = None
        
        if context.area.type == 'VIEW_3D':
            # Get target objects
            self.target_objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
            if not self.target_objects:
                self.report({'WARNING'}, "No mesh objects selected")
                return {'CANCELLED'}
            
            # Set up drawing plane based on view
            self.setup_drawing_plane(context)
            
            # Set up drawing
            self.points = []
            self.drawing = True
            self.current_depth = self.extrude_depth
            
            # Add viewport drawing handler
            args = (self, context)
            self.draw_handler = bpy.types.SpaceView3D.draw_handler_add(
                self.draw_callback_px, args, 'WINDOW', 'POST_PIXEL'
            )
            
            context.window_manager.modal_handler_add(self)
            self.report({'INFO'}, f"FreeForm Boolean ({self.operation}) - LMB: add points, RMB: adjust depth, Enter: finish, Esc: cancel")
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}
    
    def setup_drawing_plane(self, context):
        """Set up the drawing plane based on the current view"""
        rv3d = context.region_data
        
        if context.active_object and context.active_object.type == 'MESH':
            self.drawing_plane_center = context.active_object.location.copy()
        else:
            self.drawing_plane_center = Vector((0, 0, 0))
        
        # Use view direction as drawing plane normal
        view_matrix = rv3d.view_matrix
        self.drawing_plane_normal = Vector((view_matrix[0][2], view_matrix[1][2], view_matrix[2][2]))
        self.drawing_plane_normal.normalize()
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        
        if event.type == 'MOUSEMOVE':
            if self.adjusting_depth:
                # Adjust depth based on mouse Y movement
                delta_y = event.mouse_region_y - self.initial_mouse_y
                depth_change = delta_y * 0.01  # Sensitivity factor
                self.current_depth = max(0.01, self.initial_depth + depth_change)
                self.update_preview(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if not self.adjusting_depth:
                # Add point to polygon
                self.add_point(context, event)
                self.update_preview(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            if len(self.points) >= 3:
                # Start depth adjustment mode
                self.adjusting_depth = True
                self.initial_mouse_y = event.mouse_region_y
                self.initial_depth = self.current_depth
                self.report({'INFO'}, "Adjusting depth - move mouse up/down, LMB to confirm")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
            if self.adjusting_depth:
                # End depth adjustment mode
                self.adjusting_depth = False
                self.extrude_depth = self.current_depth
                self.report({'INFO'}, f"Depth set to {self.current_depth:.3f}")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELUPMOUSE':
            # Increase depth
            self.current_depth = min(10.0, self.current_depth + 0.1)
            self.extrude_depth = self.current_depth
            self.update_preview(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELDOWNMOUSE':
            # Decrease depth
            self.current_depth = max(0.01, self.current_depth - 0.1)
            self.extrude_depth = self.current_depth
            self.update_preview(context)
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
        
        elif event.type in {'ESC'}:
            # Cancel operation
            self.cleanup(context)
            return {'CANCELLED'}
        
        elif event.type == 'Z' and event.value == 'PRESS':
            # Undo last point
            if self.points:
                self.points.pop()
                self.update_preview(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'B' and event.value == 'PRESS':
            # Toggle both directions
            self.both_directions = not self.both_directions
            self.update_preview(context)
            direction_text = "both directions" if self.both_directions else "one direction"
            self.report({'INFO'}, f"Extrude mode: {direction_text}")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'TAB' and event.value == 'PRESS':
            # Cycle through boolean operations
            operations = ['DIFFERENCE', 'UNION', 'INTERSECT']
            current_index = operations.index(self.operation)
            next_index = (current_index + 1) % len(operations)
            self.operation = operations[next_index]
            self.report({'INFO'}, f"Boolean operation: {self.operation}")
            return {'RUNNING_MODAL'}
        
        return {'RUNNING_MODAL'}
    
    def add_point(self, context, event):
        """Convert mouse position to 3D world coordinate on the drawing plane"""
        region = context.region
        rv3d = context.region_data
        
        # Get mouse coordinate in region
        coord = Vector((event.mouse_region_x, event.mouse_region_y))
        
        # Cast ray from camera through mouse position
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        # Intersect ray with drawing plane
        world_pos = self.intersect_ray_plane(ray_origin, view_vector, 
                                           self.drawing_plane_center, 
                                           self.drawing_plane_normal)
        
        if world_pos:
            self.points.append(world_pos)
    
    def intersect_ray_plane(self, ray_origin, ray_direction, plane_point, plane_normal):
        """Calculate intersection of ray with plane"""
        denom = plane_normal.dot(ray_direction)
        if abs(denom) < 1e-6:
            return None  # Ray is parallel to plane
        
        t = (plane_point - ray_origin).dot(plane_normal) / denom
        if t < 0:
            return None  # Intersection is behind ray origin
        
        return ray_origin + t * ray_direction
    
    def update_preview(self, context):
        """Update the 3D preview of the extruded shape"""
        if len(self.points) < 3:
            self.preview_batch = None
            return
        
        try:
            # Create preview geometry
            vertices = self.generate_preview_vertices()
            
            if vertices and len(vertices) >= 3:
                print(f"Debug: vertices count: {len(vertices)}")
                
                # Create batch for preview without indices (simple triangulation)
                self.preview_shader = gpu.shader.from_builtin('UNIFORM_COLOR')
                self.preview_batch = batch_for_shader(
                    self.preview_shader, 'TRIANGLES', 
                    {"pos": vertices}
                )
                print("Debug: Batch created successfully")
            else:
                print("Debug: No vertices generated")
                
        except Exception as e:
            print(f"Debug: Error in update_preview: {e}")
            import traceback
            traceback.print_exc()
            self.preview_batch = None
        
    def generate_preview_vertices(self):
        """Generate vertices for 3D preview using simple triangulation"""
        if len(self.points) < 3:
            return []
        
        try:
            vertices = []
            n_points = len(self.points)
            
            # Convert points to proper positions
            bottom_verts = []
            top_verts = []
            
            for point in self.points:
                if self.both_directions:
                    bottom_pos = point - self.drawing_plane_normal * (self.current_depth / 2)
                    top_pos = point + self.drawing_plane_normal * (self.current_depth / 2)
                else:
                    bottom_pos = point.copy()
                    top_pos = point + self.drawing_plane_normal * self.current_depth
                
                bottom_verts.append((float(bottom_pos.x), float(bottom_pos.y), float(bottom_pos.z)))
                top_verts.append((float(top_pos.x), float(top_pos.y), float(top_pos.z)))
            
            # Bottom face triangles (fan triangulation)
            for i in range(1, n_points - 1):
                vertices.extend([
                    bottom_verts[0],
                    bottom_verts[i],
                    bottom_verts[i + 1]
                ])
            
            # Top face triangles (fan triangulation, reversed winding)
            for i in range(1, n_points - 1):
                vertices.extend([
                    top_verts[0],
                    top_verts[i + 1],
                    top_verts[i]
                ])
            
            # Side faces
            for i in range(n_points):
                next_i = (i + 1) % n_points
                
                # Two triangles per side face
                # Triangle 1
                vertices.extend([
                    bottom_verts[i],
                    top_verts[i],
                    bottom_verts[next_i]
                ])
                
                # Triangle 2
                vertices.extend([
                    bottom_verts[next_i],
                    top_verts[i],
                    top_verts[next_i]
                ])
            
            print(f"Generated {len(vertices)} vertices for {len(vertices)//3} triangles")
            return vertices
            
        except Exception as e:
            print(f"Error in generate_preview_vertices: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def create_boolean_mesh(self, context):
        """Create the boolean mesh from drawn points"""
        if len(self.points) < 3:
            return
        
        # Create new mesh
        mesh = bpy.data.meshes.new("FreeFormBoolean")
        obj = bpy.data.objects.new("FreeFormBoolean", mesh)
        
        # Create bmesh
        bm = bmesh.new()
        
        # Add vertices from points on the drawing plane
        verts = [bm.verts.new(pt) for pt in self.points]
        
        # Create base face
        face = bm.faces.new(verts)
        bm.faces.ensure_lookup_table()
        
        # Calculate extrusion vector
        extrude_vector = self.drawing_plane_normal * self.current_depth
        
        if self.both_directions:
            # Extrude in both directions
            # First, move the original face to the center
            bmesh.ops.translate(bm, vec=-extrude_vector/2, verts=verts)
            
            # Extrude forward
            extrude1 = bmesh.ops.extrude_face_region(bm, geom=[face])
            verts1 = [e for e in extrude1['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=extrude_vector, verts=verts1)
        else:
            # Extrude in one direction
            extrude = bmesh.ops.extrude_face_region(bm, geom=[face])
            verts_extruded = [e for e in extrude['geom'] if isinstance(e, bmesh.types.BMVert)]
            bmesh.ops.translate(bm, vec=extrude_vector, verts=verts_extruded)
        
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
                mod.solver = 'FAST'

        
        # Turn boolean object into wireframe and move to cuts collection
        from . import utils
        utils.turn_into_wireframe(obj)
        
        self.report({'INFO'}, f"FreeForm Boolean ({self.operation}) created with {len(self.points)} points, depth: {self.current_depth:.3f}")
    
    def draw_callback_px(self, op, context):
        """Draw the polygon and 3D preview in the viewport"""
        if not self.drawing:
            return
        
        try:
            # Enable depth testing and blending
            gpu.state.depth_test_set('LESS_EQUAL')
            gpu.state.blend_set('ALPHA')
            
            # Draw 3D preview
            if self.preview_batch and self.preview_shader and len(self.points) >= 3:
                # Get operation color
                if self.operation == 'DIFFERENCE':
                    color = (1.0, 0.3, 0.3, 0.3)  # Red with transparency
                elif self.operation == 'UNION':
                    color = (0.3, 1.0, 0.3, 0.3)  # Green with transparency
                else:  # INTERSECT
                    color = (0.3, 0.3, 1.0, 0.3)  # Blue with transparency
                
                self.preview_shader.bind()
                self.preview_shader.uniform_float("color", color)
                self.preview_batch.draw(self.preview_shader)
            
            # Draw 2D overlay (points and lines)
            self.draw_2d_overlay(context)
            
        except Exception as e:
            print(f"Error in draw_callback_px: {e}")
        finally:
            # Restore OpenGL defaults
            gpu.state.depth_test_set('NONE')
            gpu.state.blend_set('NONE')
        
    def draw_2d_overlay(self, context):
        """Draw 2D overlay elements"""
        if not self.points:
            return
        
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
            
            # Close the polygon if we have enough points
            if len(screen_points) >= 3:
                coords.extend([screen_points[-1], screen_points[0]])
            
            # Add line from last point to mouse (preview)
            if screen_points and not self.adjusting_depth:
                coords.extend([screen_points[-1], self.mouse_pos])
            
            batch = batch_for_shader(shader, 'LINES', {"pos": coords})
            
            # Set color based on operation
            if self.operation == 'DIFFERENCE':
                line_color = (1.0, 0.4, 0.4, 0.8)  # Red
            elif self.operation == 'UNION':
                line_color = (0.4, 1.0, 0.4, 0.8)  # Green
            else:  # INTERSECT
                line_color = (0.4, 0.4, 1.0, 0.8)  # Blue
            
            shader.bind()
            shader.uniform_float("color", line_color)
            batch.draw(shader)
        
        # Draw points as circles
        for screen_point in screen_points:
            self.draw_circle(screen_point, 4, (1.0, 1.0, 1.0, 1.0))
        
        # Draw depth indicator
        if len(self.points) >= 3:
            self.draw_depth_indicator(context)
    
    def draw_depth_indicator(self, context):
        """Draw depth value on screen"""
        import blf
        
        font_id = 0
        blf.position(font_id, 50, 50, 0)
        blf.size(font_id, 20)
        blf.color(font_id, 1, 1, 1, 1)
        
        depth_text = f"Depth: {self.current_depth:.3f}"
        if self.adjusting_depth:
            depth_text += " (adjusting)"
        
        blf.draw(font_id, depth_text)
        
        # Draw operation indicator
        blf.position(font_id, 50, 80, 0)
        op_color = {
            'DIFFERENCE': (1.0, 0.4, 0.4, 1.0),
            'UNION': (0.4, 1.0, 0.4, 1.0),
            'INTERSECT': (0.4, 0.4, 1.0, 1.0)
        }
        color = op_color.get(self.operation, (1, 1, 1, 1))
        blf.color(font_id, *color)
        blf.draw(font_id, f"Operation: {self.operation}")
        
        # Draw controls help
        blf.position(font_id, 50, 110, 0)
        blf.color(font_id, 0.8, 0.8, 0.8, 1)
        blf.size(font_id, 12)
        
        controls = [
            "LMB: Add point",
            "RMB: Adjust depth",
            "Wheel: Change depth",
            "Tab: Change operation",
            "B: Toggle both directions",
            "Z: Undo point",
            "Enter: Finish",
            "Esc: Cancel"
        ]
        
        for i, control in enumerate(controls):
            blf.position(font_id, 50, 110 + i * 15, 0)
            blf.draw(font_id, control)
    
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
        self.preview_batch = None
        self.preview_shader = None
        context.area.tag_redraw()
    
    def draw(self, context):
        """Draw the operator properties in the dialog"""
        layout = self.layout
        layout.prop(self, "operation")
        layout.prop(self, "extrude_depth")
        layout.prop(self, "both_directions")
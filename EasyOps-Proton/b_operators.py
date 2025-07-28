# Freeform drawing
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
from bpy.props import EnumProperty, FloatProperty, BoolProperty

from . import utils

class OBJECT_OT_easy_free_boolean_base(bpy.types.Operator):
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

    camera_navigation: BoolProperty(
        name="Camera Navigation Mode",
        description="Toggle between drawing and camera navigation",
        default=False
    )    

    grid_snap: BoolProperty(
        name="Grid Snap",
        description="Snap points to grid",
        default=True
    )

    axis_lock: EnumProperty(
        name="Axis Lock",
        description="Lock drawing to specific axis",
        items=[
            ('NONE', "None", "No axis lock"),
            ('X', "X-Axis", "Lock to X Axis"),
            ('Y', "Y-Axis", "Lock to Y Axis"),
            ('Z', "Z-Axis", "Lock to Z axis"),
        ],
        default='NONE'
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

        self.shift_held = False

        self.grid_size = self.get_grid_size(context)
        self.axis_lock_modes = ['NONE', 'X', 'Y']
        self.current_axis_index = 0
        
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
    
    def get_grid_size(self, context):
        space = context.space_data
        if hasattr(space, 'overlay') and hasattr(space.overlay, 'grid_scale'):
            return space.overlay.grid_scale
        return 1.0
    
    # Wrong Impl. keeping it because its useful
    def snap_to_grid(self, point, grid_size):
        """Snap point to grid"""
        if not self.points:
            return point

        return Vector((
            round(point.x / grid_size) * grid_size,
            round(point.y / grid_size) * grid_size,
            round(point.z / grid_size) * grid_size
        ))
    
    def snap_to_angle(self, point, context, snap_angle=15.0):
        """Snap point to angular increments"""
        if not self.points:
            return point

        reference_point = self.points[-1]

        direction = point - reference_point

        if direction.length < 0.01:
            return point

        plane_up = Vector((0, 0, 1))
        if abs(self.drawing_plane_normal.dot(plane_up)) > 0.9:
            plane_up = Vector((1, 0, 0))
        
        plane_right = self.drawing_plane_normal.cross(plane_up).normalized()
        plane_up = plane_right.cross(self.drawing_plane_normal).normalized()

        # Project direction onto the 2D plane
        x_component = direction.dot(plane_right)
        y_component = direction.dot(plane_up)

        # Angle in degrees
        angle_rad = math.atan2(y_component, x_component)
        angle_deg = math.degrees(angle_rad)

        snapped_angle_deg = round(angle_deg / snap_angle) * snap_angle
        snapped_angle_rad = math.radians(snapped_angle_deg)

        distance = direction.length
        snapped_direction = (plane_right * math.cos(snapped_angle_rad) +
            plane_up * math.sin(snapped_angle_rad)) * distance

        return reference_point + snapped_direction

    def snap_to_increments(self, point, context, increment=0.05):
        """Snap to distance increments from reference point"""
        if not self.points:
            return point

        reference_point = self.points[-1]
        direction = point - reference_point

        if direction.length < 0.01:
            return point

        # Snap the distance to increments
        distance = direction.length
        snapped_distance = round(distance / increment) * increment

        normalized_direction = direction.normalized()
        return reference_point + normalized_direction * snapped_distance

    def apply_axis_lock(self, world_pos, context):
        """Apply axis lock constraint to current world position"""
        if self.axis_lock == 'NONE' or not self.points:
            return world_pos

        reference_point = self.points[-1]

        """ 
        World Axis Lock

        if self.axis_lock == 'X':
            return Vector((world_pos.x, reference_point.y, reference_point.z))
        elif self.axis_lock == 'Y':
            return Vector((reference_point.x, world_pos.y, reference_point.z))
        elif self.axis_lock == 'Z':
            return Vector((reference_point.x, reference_point.y, world_pos.z))
        """
        
        plane_normal = self.drawing_plane_normal.normalized()

        world_up = Vector((0, 0, 1))
        if abs(plane_normal.dot(world_up)) > 0.9:
            world_up = Vector((1, 0, 0)) # Nearly parallel to world up -> switch to world
        
        local_x = plane_normal.cross(world_up).normalized()
        local_y = local_x.cross(plane_normal).normalized()
        local_z = plane_normal

        offset_vector = world_pos - reference_point

        if self.axis_lock == 'X':
            local_x_component = offset_vector.dot(local_x)
            return reference_point + local_x * local_x_component
        elif self.axis_lock == 'Y':
            local_y_component = offset_vector.dot(local_y)
            return reference_point + local_y * local_y_component

        return world_pos

    def setup_drawing_plane(self, context):
        """Set up the drawing plane based on the current view"""
        rv3d = context.region_data
        

        self.drawing_plane_center = Vector((0, 0, 0))
        
        # Use view direction as drawing plane normal
        view_matrix = rv3d.view_matrix.inverted()

        self.drawing_plane_normal = -view_matrix.col[2].to_3d() # Easier fix
        self.drawing_plane_normal.normalize()

        # Orthographic fix
        if rv3d.is_orthographic_side_view:
            abs_normal = Vector((abs(self.drawing_plane_normal.x), 
                            abs(self.drawing_plane_normal.y), 
                            abs(self.drawing_plane_normal.z)))
            
            max_component = max(abs_normal)
            
            if abs_normal.x == max_component:
                self.drawing_plane_normal = Vector((1, 0, 0)) if self.drawing_plane_normal.x > 0 else Vector((-1, 0, 0))
            elif abs_normal.y == max_component:
                self.drawing_plane_normal = Vector((0, 1, 0)) if self.drawing_plane_normal.y > 0 else Vector((0, -1, 0))
            else:
                self.drawing_plane_normal = Vector((0, 0, 1)) if self.drawing_plane_normal.z > 0 else Vector((0, 0, -1))

            
    
    def modal(self, context, event):
        context.area.tag_redraw()
        
        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.shift_held = event.shift

        snap_enabled = self.grid_snap and not event.shift
        
        if event.type == 'C' and event.value == 'PRESS':
            self.camera_navigation = not self.camera_navigation
            self.update_wireframe_preview(context)

            mode_text = "Camera Navigation" if self.camera_navigation else "Drawing"
            self.report({'INFO'}, f"Switched to {mode_text} mode")
            return {'RUNNING_MODAL'}
        
        if event.type == 'X' and event.value == 'PRESS':
            self.current_axis_index = (self.current_axis_index + 1) % len(self.axis_lock_modes)
            self.axis_lock = self.axis_lock_modes[self.current_axis_index]

            if self.axis_lock == 'NONE':
                lock_text = "No axis lock"
            else:
                lock_text = f"Locked to {self.axis_lock}-axis"

            self.report({'INFO'}, f"Axis lock: {lock_text}")
            return {'RUNNING_MODAL'} 

        if self.camera_navigation:
            return {'PASS_THROUGH'}
        
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
                self.add_point(context, event, snap_enabled)
                self.update_preview(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RIGHTMOUSE' and event.value == 'PRESS':
            if len(self.points) >= 3:
                # Start depth adjustment mode
                self.adjusting_depth = True
                self.initial_mouse_y = event.mouse_region_y
                self.initial_depth = self.current_depth
                self.update_wireframe_preview(context)

                self.report({'INFO'}, "Adjusting depth - move mouse up/down, LMB to confirm")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'RIGHTMOUSE' and event.value == 'RELEASE':
            if self.adjusting_depth:
                # End depth adjustment mode
                self.adjusting_depth = False
                self.extrude_depth = self.current_depth
                self.update_wireframe_preview(context)

                self.report({'INFO'}, f"Depth set to {self.current_depth:.3f}")
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELUPMOUSE':
            # Increase depth
            self.current_depth = min(10.0, self.current_depth + 0.1)
            self.extrude_depth = self.current_depth
            self.update_preview(context)
            self.update_wireframe_preview(context)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'WHEELDOWNMOUSE':
            # Decrease depth
            self.current_depth = max(0.01, self.current_depth - 0.1)
            self.extrude_depth = self.current_depth
            self.update_preview(context)
            self.update_wireframe_preview(context)
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
            self.update_wireframe_preview(context)

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
    
    # Surface drawing
    def get_surface_point_and_normal(self, context, event):
        """Get surface point and the normal from mouse position with raycasting"""
        if not self.target_objects:
            return None, None

        region = context.region
        rv3d = context.region_data

        coord = Vector((event.mouse_region_x, event.mouse_region_y))

        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)

        # Try a raycast on each target object
        for obj in self.target_objects:
            if obj.type != 'MESH':
                continue

            # Convert the ray into object's local space
            obj_matrix_inv = obj.matrix_world.inverted()
            local_ray_origin = obj_matrix_inv @ ray_origin
            local_ray_direction = (obj_matrix_inv @ (ray_origin + view_vector))
            local_ray_direction.normalize()

            # Perform raycast
            depsgraph = context.evaluated_depsgraph_get()
            obj_eval = obj.evaluated_get(depsgraph)

            bm = bmesh.new()
            bm.from_mesh(obj_eval.data)
            bm.transform(obj.matrix_world)

            bvh = BVHTree.FromBMesh(bm)

            hit_point, hit_normal, hit_index, hit_distance = bvh.ray_cast(ray_origin, view_vector)

            bm.free()

            if hit_point:
                return hit_point, hit_normal
        
        return None, None
    
    # Same same but different
    def setup_surface_drawing_plane(self, context, surface_point, surface_normal):
        self.drawing_plane_center = surface_point
        self.drawing_plane_normal = surface_normal.normalized()

        # Ensure normal points can be seen by the camera (This does not mean depth extends towards the camera)
        rv3d = context.region_data
        view_matrix = rv3d.view_matrix.inverted()
        camera_direction = -view_matrix.col[2].to_3d().normalized()

        if self.drawing_plane_normal.dot(camera_direction) < 0:
            self.drawing_plane_normal = -self.drawing_plane_normal
    

    def add_point(self, context, event, snap_enabled=True):
        if utils.is_surface_drawing_enabled(context):
            surface_point, surface_normal = self.get_surface_point_and_normal(context, event)
            
            if surface_point and surface_normal:
                self.setup_surface_drawing_plane(context, event)
                world_pos = surface_point
            else:
                world_pos = self.get_plane_intersection_point(context, event)
        
        else:
            # Regular plane drawing
            world_pos = self.get_plane_intersection_point(context, event)
        
        if world_pos:
            world_pos = self.apply_axis_lock(world_pos, context)

            if snap_enabled:
                world_pos = self.snap_to_angle(world_pos, context, snap_angle=15.0)
                world_pos = self.snap_to_increments(world_pos, context, increment=0.05)
        
        self.points.append(world_pos)
    

    def get_plane_intersection_point(self, context, event):
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
        
        # Ray-plane intersection is currently failing on some axises, this should be the fix->
        if world_pos is None:
            # Use region_2d_to_location_3d as a fallback since it seems to be weird on some orthographic views
            world_pos = view3d_utils.region_2d_to_location_3d(
                region, rv3d, coord, self.drawing_plane_center
            )
        return world_pos
        
    
    def intersect_ray_plane(self, ray_origin, ray_direction, plane_point, plane_normal):
        """Calculate intersection of ray with plane"""
        ray_direction = ray_direction.normalized()
        plane_normal = plane_normal.normalized()

        denom = plane_normal.dot(ray_direction)

        if abs(denom) < 1e-4: # Edit threshold for parallel checks
            return None  # Ray is parallel to plane
        
        t = (plane_point - ray_origin).dot(plane_normal) / denom
        
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

        
        # Turn boolean object into wireframe and move to cuts collection
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
            
            # Freeview for FF
            if hasattr(self, 'wireframe_batch') and self.wireframe_batch and hsattr(self, 'wireframe_shader') and self.wireframe_shader:
                if self.operation == 'DIFFERENCE':
                    color = (1.0, 0.5, 0.5, 0.8)  # Red with transparency
                elif self.operation == 'UNION':
                    color = (0.5, 1.0, 0.5, 0.8)  # Green with transparency
                else:  # INTERSECT
                    color = (0.5, 0.5, 1.0, 0.8)  # Blue with transparency
                
                self.wireframe_shader.bind()
                self.wireframe_shader.uniform_float("color", wire_color)
                self.wireframe_batch.draw(self.wireframe_shader)
            
            # Temporarily disable depth testing for 2D overlays to ensure invsibility in Ortho views
            gpu.state.depth_test_set('NONE')

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
        
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')
        
        # Set color based on operation
        if self.operation == 'DIFFERENCE':
            line_color = (1.0, 0.4, 0.4, 0.8)  # Red
        elif self.operation == 'UNION':
            line_color = (0.4, 1.0, 0.4, 0.8)  # Green
        else:  # INTERSECT
            line_color = (0.4, 0.4, 1.0, 0.8)  # Blue

        if len(screen_points) >= 3:
            try:
                fill_coords = []
                for i in range(1, len(screen_points) - 1):
                    fill_coords.extend([
                        screen_points[0],
                        screen_points[i],
                        screen_points[i + 1]
                    ])

                if fill_coords:
                    fill_batch = batch_for_shader(shader, 'TRIANGLES', {"pos": fill_coords})
                    shader.bind()
                    shader.uniform_float("color", fill_color)
                    fill_batch.draw(shader)
            except Exception as e:
                print(f"Error drawing fill: {e}")

        if len(screen_points) >= 2:         
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
            
            shader.bind()
            shader.uniform_float("color", line_color)
            batch.draw(shader)
        
        # Draw points as circles (always visible)
        for i, screen_point in enumerate(screen_points):
            if i == 0:
                self.draw_circle(screen_point, 6, (1.0, 1.0, 0.0, 1.0))
            else:
                self.draw_circle(screen_point, 4, (1.0, 1.0, 1.0, 1.0))
        
        # Draw larger circle when not adjusting depth, notifies user its no longer changing
        if not self.adjusting_depth:
            if self.axis_lock != 'NONE':
                circle_color = (1.0, 1.0, 0.0, 0.8)
            elif not self.shift_held:
                circle_color = (0.0, 1.0, 0.0, 0.8)
            else:
                circle_color = (1.0, 0.0, 0.0, 0.8)
            
            self.draw_circle(self.mouse_pos, 3, circle_color)

        # Draw depth indicator
        if len(self.points) >= 1:
            self.draw_depth_indicator(context) # (inf.) HELLO? THIS IS ALREADY HERE WHY ARENT YOU BEING CALLED??
    
    def draw_depth_indicator(self, context):
        """Draw depth value on screen"""

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

        # Draw axis lock status
        blf.position(font_id, 50, 140, 0)
        if self.axis_lock == 'NONE':
            lock_color = (0.8, 0.8, 0.8, 1.0)
            lock_text = "Axis Lock: None"
        else:
            lock_color = (1.0, 1.0, 0.4, 1.0)
            lock_text = f"Axis Lock: {self.axis_lock}-axis"
        blf.color(font_id, *lock_color)
        blf.draw(font_id, lock_text)
        
        # Draw controls help
        blf.position(font_id, 50, 170, 0)
        blf.color(font_id, 0.8, 0.8, 0.8, 1)
        blf.size(font_id, 12)
        
        controls = [
            "LMB: Add point",
            "RMB: Adjust depth",
            "Wheel: Change depth",
            "Tab: Change operation",
            "C: Change Camera/Drawing Mode",
            "X: Cycle axis lock",
            "B: Toggle both directions",
            "Z: Undo point",
            "Shift: (Hold) Turn off snap-to-grid",
            "Enter: Finish",
            "Esc: Cancel"
        ]
        
        for i, control in enumerate(controls):
            blf.position(font_id, 50, 170 + i * 15, 0)
            blf.draw(font_id, control)
    
    # Confusing func. name, it's a vertex circle not an actual circle
    def draw_circle(self, center, radius, color):
        """Draw a simple circle at screen coordinates"""
        
        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        coords_filled = [center]
        segments = 16
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            coords_filled.append((x, y))
        
        # Generate circle vertices
        segments = 16
        coords = []
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            coords.append((x, y))
        
        batch_filled = batch_for_shader(shader, 'TRI_FAN', {"pos": coords_filled})
        shader.bind()
        fill_color = (color[0], color[1], color[2], color[3] * 0.6)
        shader.uniform_float("color", fill_color)
        batch_filled.draw(shader)

        coords_filled = [center]
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = center[0] + radius * math.cos(angle)
            y = center[1] + radius * math.sin(angle)
            coords_filled.append((x, y))

        batch = batch_for_shader(shader, 'LINE_STRIP', {"pos": coords})
        shader.uniform_float("color", color)
        batch.draw(shader)
    
    def cleanup(self, context):
        """Clean up the drawing handler"""
        if self.draw_handler:
            bpy.types.SpaceView3D.draw_handler_remove(self.draw_handler, 'WINDOW')
            self.draw_handler = None
        
        if hasattr(self, 'wireframe_obj') and self.wireframe_obj:
            bpy.data.objects.remove(self.wireframe_obj, do_unlink=True)
            self.wireframe_obj = None

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
    
    def update_wireframe_preview(self, context):
        """Create or update a wireframe object showing the FF boolean"""
        if hasattr(self, 'wireframe_obj') and self.wireframe_obj:
            bpy.data.objects.remove(self.wireframe_obj, do_unlink=True)

        if len(self.points) < 3:
            return
        
        mesh = bpy.data.meshes.new("FF_PREVIEW_MESH")
        obj = bpy.data.objects.new("FF_PREVIEW", mesh)
        context.collection.objects.link(obj)

        bm = bmesh.new()
        bottom = []
        top = []

        for pt in self.points:
            if self.both_directions:
                bottom_pt = pt - self.drawing_plane_normal * (self.current_depth / 2)
                top_pt = pt + self.drawing_plane_normal * (self.current_depth / 2)
            else:
                bottom_pt = pt
                top_pt = pt + self.drawing_plane_normal * self.current_depth

            bottom.append(bm.verts.new(bottom_pt))
            top.append(bm.verts.new(top_pt))

        bm.verts.ensure_lookup_table()

        for i in range(len(bottom)):
            next_i = (i + 1) % len(bottom)
            bm.faces.new([bottom[i], bottom[next_i], top[next_i], top[i]])

        bm.to_mesh(mesh)
        bm.free()
        
        obj.display_type = 'WIRE'
        obj.show_in_front = True
        obj.hide_select = True
        self.wireframe_obj = obj

class OBJECT_OT_easy_freeform_boolean(OBJECT_OT_easy_free_boolean_base):
    """Draw freeform boolean shapes in the viewport with real-time preview"""
    bl_idname = "object.easy_freeform_boolean"
    bl_label = "FreeForm Boolean"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    

# Next plan is to integrate these 'drawing templates' such as Squares or Circles, hopefully we can inherity the FF Boolean class and just use some of their helper functions
# This bug is BUGGING me -> Why does this make the Freeform boolean class unregister?? What going on
class OBJECT_OT_easy_rectangle_boolean(OBJECT_OT_easy_free_boolean_base):
    """Draw rectangles/squares with a drag to re-size controls"""
    bl_idname = "object.easy_rectangle_boolean"
    bl_label = "Rectangle Boolean"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}

    # Class specific
    maintain_aspect: BoolProperty(
        name="Square Mode",
        description="Maintain 1:1 aspect ratio",
        default=False
    )

    def invoke(self, context, event):
        self.start_point = None
        self.current_point = None
        self.is_dragging = False
        self.rectangle_defined = False

        result = super().invoke(context, event)

        if result == {'RUNNING_MODAL'}:
            self.report({'INFO'}, f"Rectnagle Boolean ({self.operation}) - LMB + Drag: Define Rectangle, RMB: Adjust Depth, Enter: Finish, Esc: Cancel")

        return result

    def modal(self, context, event):
        context.area.tag_redraw()

        # Handle rectangle-specific input
        if not self.rectangle_defined:
            return self.handle_rectangle_input(context, event)
        else:
            return super().modal(context, event)
            # Parent modal for depth adjustment works just fine above
    
    
    def handle_rectangle_input(self, context, event):
        """Input for JUST the definition phase"""
        self.mouse_pos = Vector((event.mouse_region_x, event.mouse_region_y))
        self.shift_held = event.shift

        # Handle camera navigation
        if event.type == 'C' and event.value == 'PRESS':
            self.camera_navigation = not self.camera_navigation
            mode_text = "Camera Navigation" if self.camera_navigation else "Drawing Mode"
            self.update_preview(context)
            self.update_wireframe_preview(context)
            self.report({'INFO'}, f"Switched to {mode_text} mode")
            return {'RUNNING_MODAL'}

        if self.camera_navigation:
            return {'PASS_THROUGH'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if not self.is_dragging:
                # Start rectangle definition -> Doesn't overlap with depth definition
                self.start_rectangle(context, event)
                self.update_preview(context)
                return {'RUNNING_MODAL'}

        elif event.type == 'MOUSEMOVE':
            if self.is_dragging:
                self.update_rectangle(context, event)
                return {'RUNNING_MODAL'}

        elif event.type == 'LEFTMOUSE' and event.value == 'RELEASE':
            if self.is_dragging:
                self.finish_rectangle(context, event)
                return {'RUNNING_MODAL'}
        
        elif event.type == 'S' and event.value == 'PRESS':
            # Toggle 1:1 (Square) definition mode
            self.maintain_aspect = not maintain_aspect
            mode_text = "Square" if self.maintain_aspect else "Rectangle"
            self.report({'INFO'}, f"Mode: {mode_text}")
            if self.is_dragging:
                self.update_rectangle(context, event)
            return {'RUNNING_MODAL'}
        
        elif event.type == 'TAB' and event.value == 'PRESS':
            # Cycle boolean operations
            operations = ['DIFFERENCE', 'UNION', 'INTERSECT']
            current_index = operations.index(self.operations)
            next_index = (current_index + 1) % len(operations)
            self.operation = operations[next_index]
            self.report({'INFO'}, f"Boolean operation: {self.operation}")
            return {'RUNNING_MODAL'}
        
        elif event.type in {'ESC'}:
            # Cancel operation
            self.cleanup(context)
            return {'CANCELLED'}
            
        return {'RUNNING_MODAL'}

    def start_rectangle(self, context, event):
        """Start rectangle definition by defining the first corner"""
        self.start_point = self.mouse_to_world_point(context, event)
        self.current_point = self.start_point.copy()
        self.is_dragging = True

        self.points = []

    def update_rectangle(self, context, event):
        """Update dimensions while dragging"""
        if not self.start_point:
            return

        self.update_preview(context)
        self.update_wireframe_preview(context)

        raw_point = self.mouse_to_world_point(context, event)
        self.current_point = self.add_grid_snapping(raw_point, context)
        self.generate_rectangle_points()

        # Update preview
        self.update_preview(context)
        self.update_wireframe_preview(context)

    
    def finish_rectangle(self, context, event):
        """Switch to depth adjustment"""
        if not self.start_point or not self.current_point:
            return
        
        self.is_dragging = False
        self.rectangle_defined = True

        self.generate_rectangle_points()
        # Generate final rectangle points

        self.update_preview(context)
        self.update_wireframe_preview(context)


        self.report({'INFO'}, f"Rectangle defined. RMB: Adjust Depth, Wheel: Change Depth, Enter: Finish")
    
    def generate_rectangle_points(self):
        """Generate corner point plots of rectangles"""
        if not self.start_point or not self.current_point:
            return
        
        start = self.start_point
        current = self.current_point

        # Calculate in world space then project the points
        plane_normal = self.drawing_plane_normal.normalized()

        # Create local co-ord system on the drawing plane
        world_up = Vector((0, 0 , 1))
        if abs(plane_normal.dot(world_up)) > 0.9:
            world_up = Vector((1, 0, 0))
    
        local_x = plane_normal.cross(world_up).normalized()
        local_y = local_x.cross(plane_normal).normalized()

        # Get dimensions in local plane
        offset = current - start
        width = offset.dot(local_x)
        height = offset.dot(local_y)

        # Square mode application
        if self.maintain_aspect:
            size = max(abs(width), abs(height))
            width = size if width >= 0 else -size
            height = size if height >= 0 else -size
        
        corner1 = start
        corner2 = start + local_x * width
        corner3 = start + local_x * width + local_y * height
        corner4 = start + local_y * height

        self.points = [corner1, corner2, corner3, corner4]
    
    # Override
    def draw_2d_overlay(self, context):
        if not self.points and not self.is_dragging:
            return
        self.draw_depth_indicator(context)
        region = context.region
        rv3d = context.region_data

        if self.operation == 'DIFFERENCE':
            line_color = (1.0, 0.4, 0.4, 0.8)  # Red
            fill_color = (1.0, 0.4, 0.4, 0.2)  # Red with transparency
        elif self.operation == 'UNION':
            line_color = (0.4, 1.0, 0.4, 0.8)  # Green
            fill_color = (0.4, 1.0, 0.4, 0.2)  # Green with transparency
        else:  # INTERSECT
            line_color = (0.4, 0.4, 1.0, 0.8)  # Blue
            fill_color = (0.4, 0.4, 1.0, 0.2)  # Blue with transparency

        shader = gpu.shader.from_builtin('UNIFORM_COLOR')

        # Draw rectangle outline and fill (if possible)
        if len(self.points) >= 4:
            screen_points = []
            for point in self.points:
                screen_coord = view3d_utils.location_3d_to_region_2d(region, rv3d, point)
                if screen_coord:
                    screen_points.append(screen_coord)

            if len(screen_points) == 4:
                try:
                    fill_coords = [
                        screen_points[0], screen_points[1], screen_points[2],
                        screen_points[0], screen_points[2], screen_points[3]
                    ]

                    fill_batch = batch_for_shader(shader, 'TRIANGLES', {"pos": fill_coords})
                    shader.bind()
                    shader.uniform_float("color", fill_color)
                    fill_batch.draw(shader)

                except Exception as e:
                    print(f"Error drawing rectangle fill: {e}")
            
                line_coords = [
                    screen_points[0], screen_points[1],
                    screen_points[1], screen_points[2],
                    screen_points[2], screen_points[3],
                    screen_points[3], screen_points[0]
                ]

                line_batch = batch_for_shader(shader, 'LINES', {"pos": line_coords})
                shader.bind()
                shader.uniform_float("color", line_color)
                line_batch.draw()

                # Draw corner points
                for i, screen_point in enumerate(screen_points):
                    if i == 0:
                        self.draw_circle(screen_point, 6, (1.0, 1.0, 0.0, 1.0))
                    else:
                        self.draw_circle(screen_point, 4, (1.0, 1.0, 1.0, 1.0))

        elif self.is_dragging and self.start_point:
            start_screen = view3d_utils.location_3d_to_region_2d(region, rv3d, self.start_point)
            if start_screen:
                coords = [start_screen, self.mouse_pos]
                batch = batch_for_shader(shader, 'LINES', {"pos": coords})
                shader.bind()
                shader.uniform_float("color", line_color)
                batch.draw(shader)

                self.draw_circle(start_screen, 6, (1.0, 1.0, 0.0, 1.0))
        
        # Cursor indicator
        if not self.rectangle_defined:
            cursor_color = (0.0, 1.0, 0.0, 0.8) if not self.maintain_aspect else (1.0, 1.0, 0.0, 0.8)
            self.draw_circle(self.mouse_pos, 3, cursor_color)
        
        """
            song of the commit: i wait for you
        """


    def draw_depth_indicator(self, context):
        """Depth value and controls"""

        font_id = 0
        blf.size(font_id, 20)

        # Draw depth info
        blf.position(font_id, 50, 50, 0)
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

        # Draw mode indicator
        blf.position(font_id, 50, 110, 0)
        mode_color = (1.0, 1.0, 0.4, 1.0) if self.maintain_aspect else (0.8, 0.8, 0.8, 1.0)
        blf.color(font_id, *mode_color)
        mode_text = "Square" if self.maintain_aspect else "Rectangle"
        blf.draw(font_id, f"Mode: {mode_text}")

        # Draw controls
        blf.position(font_id, 50, 140, 0)
        blf.color(font_id, 0.8, 0.8, 0.8, 1)
        blf.size(font_id, 12)

        if not self.rectangle_defined:
            controls = [
                "LMB+Drag: Define rectangle",
                "S: Toggle Square/Rectangle mode",
                "Tab: Change operation",
                "C: Camera/Drawing mode",
                "Esc: Cancel"
            ]
        else:
            controls = [
                "RMB: Adjust depth",
                "S: Toggle Square/Rectangle mode",
                "Wheel: Change depth",
                "Tab: Change operation",
                "B: Toggle both directions",
                "Enter: Finish",
                "Esc: Cancel"
            ]

            for i, control in enumerate(controls):
                blf.position(font_id, 50, 140 + i * 15, 0)
                blf.draw(font_id, control)

    def mouse_to_world_point(self, context, event):
        if utils.is_surface_drawing_enabled(context):
            surface_point, surface_normal = self.get_surface_point_and_normal(context, event)

            if surface_point and surface_normal:
                # Update drawing plane for surface drawing
                self.setup_surface_drawing_plane(context, surface_point, surface_normal)
                return surface_point
            else:
                return self.get_plane_intersection_point(context, event)
        else:
            return self.get_plane_intersection_point(context, event)

    def get_plane_intersection_point(self, context, event):
        region = context.region
        rv3d = context.region_data
        
        coord = Vector((event.mouse_region_x, event.mouse_region_y))
        view_vector = view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
        ray_origin = view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)
        
        world_pos = self.intersect_ray_plane(ray_origin, view_vector, 
                                           self.drawing_plane_center, 
                                           self.drawing_plane_normal)
        
        if world_pos is None:
            world_pos = view3d_utils.region_2d_to_location_3d(
                region, rv3d, coord, self.drawing_plane_center
            )
        
        return world_pos
    
    def setup_drawing_plane(self, context):
        """Depth direction for rectangles is associated with strictly the normals on the plane mesh, not the current view"""
        rv3d = context.region_data

        self.drawing_plane_center = Vector((0, 0, 0))

        view_matrix = rv3d.view_matrix.inverted()

        self.drawing_plane_normal = -view_matrix.col[2].to_3d()
        # Consistently follows the plane normal
        self.drawing_plane_normal.normalize()

        if rv3d.is_orthographic_side_view:
            abs_normal = Vector((abs(self.drawing_plane_normal.x),
            abs(self.drawing_plane_normal.y),
            abs(self.drawing_plane_normal.z)))

            max_component = max(abs_normal)

            if abs_normal.x == max_component:
                self.drawing_plane_normal = Vector((1, 0, 0)) if self.drawing_plane_normal.x > 0 else Vector((-1, 0, 0))
            elif abs_normal.y == max_component:
                self.drawing_plane_normal = Vector((0, 1, 0)) if self.drawing_plane_normal.y > 0 else Vector((0, -1, 0))
            else:
                self.drawing_plane_normal = Vector((0, 0, 1)) if self.drawing_plane_normal.z > 0 else Vector((0, 0, -1))

    def add_grid_snapping(self, point, context):
        if not self.grid_snap or self.shift_held:
            return point
        
        grid_size = self.get_grid_size(context)

        # Create local co-ord system on the drawin gplane
        plane_normal = self.drawing_plane_normal.normalized()
        world_up = Vector((0, 0, 1))
        if abs(plane_normal.dot(world_up)) > 0.9:
            world_up = Vector((1, 0, 0))
        
        local_x = plane_normal.cross(world_up).normalized()
        local_y = local_x.cross(plane_normal).normalized()

        # Project point onto the drawing plane co-ords
        if self.start_point:
            offset = point - self.start_point
            x_comp = offset.dot(local_x)
            y_comp = offset.dot(local_y)

            snapped_x = round(x_comp / grid_size) * grid_size
            snapped_y = round(y_comp / grid_size) * grid_size

            # Convert to world Coords
            return self.start_point + local_x * snapped_x + local_y * snapped_y
        
        return point
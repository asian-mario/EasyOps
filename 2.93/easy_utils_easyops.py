bl_info = {
    "name": "Easy Utils & EasyOps",
    "blender": (2, 93, 0),
    "category": "Object",
}

import bpy
import math

# Custom Properties (can be modified by the user)
class EasyUtilsProperties(bpy.types.PropertyGroup):
    rename_prefix: bpy.props.StringProperty(
        name="Rename Prefix",
        description="Prefix for auto-renaming objects and meshes",
        default="AK-"
    )
    island_margin: bpy.props.FloatProperty(
        name="Island Margin",
        description="Margin between UV islands for Smart UV Unwrap",
        default=0.02,
        min=0.0,
        max=1.0
    )
    enable_auto_smooth: bpy.props.BoolProperty(
        name="Enable Auto Smooth",
        description="Enable or disable Auto Smooth after applying Shade Smooth",
        default=False
    )
    auto_smooth_angle: bpy.props.FloatProperty(
        name="Auto Smooth Angle",
        description="Angle for Auto Smooth (0 to 180 degrees)",
        default=30.0,
        min=0.0,
        max=180.0
    )

# Panel in a Custom "Easy Utils" and "EasyOps" Tab
class EasyUtilsPanel(bpy.types.Panel):
    bl_label = "Easy Utils"
    bl_idname = "OBJECT_PT_easy_utils"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Utils"  # This creates a new tab in the 3D Viewport

    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_utils_props

        layout.prop(props, "rename_prefix")
        layout.operator("object.easy_auto_rename", text="Auto Rename")
        layout.separator()  # Adds a visual separator between buttons   
        
        # Quick actions buttons
        layout.label(text="Quick Actions:")
        layout.prop(props, "island_margin")  # Add island margin setting for Smart UV Unwrap
        layout.operator("object.easy_smart_uv_unwrap", text="Smart UV Unwrap")

        # Shade Smooth and Auto Smooth Options
        layout.prop(props, "enable_auto_smooth")  # Checkbox for Auto Smooth
        layout.prop(props, "auto_smooth_angle")  # Angle input for Auto Smooth
        layout.operator("object.easy_shade_smooth", text="Shade Smooth")
        layout.operator("object.easy_remove_doubles", text="Remove Doubles (Merge by Distance)")

# New EasyOps Panel
class EasyOpsPanel(bpy.types.Panel):
    bl_label = "EasyOps"
    bl_idname = "OBJECT_PT_easy_ops"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Utils"  # Same tab, different section

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.label(text="Bevel & Boolean Operations")
        layout.operator("object.easy_bevel", text="Bevel")
        layout.operator("object.easy_boolean_difference", text="Boolean Difference")
        layout.operator("object.easy_boolean_union", text="Boolean Union")
        layout.operator("object.easy_boolean_intersect", text="Boolean Intersect")
        layout.separator()
        
        layout.label(text="Modifiers and Cleanup")
        layout.operator("object.easy_smart_decimate", text="Smart Decimate")
        layout.operator("object.easy_sharpen_edges", text="Flat Shading")
        layout.operator("object.easy_clean_geometry", text="Clean Geometry")
        layout.operator("object.easy_smart_apply", text="Smart Apply")
        
        # Modifier adjustment section
        if obj and obj.type == 'MESH':
            layout.separator()
            layout.label(text="Modifier Controls")

            # Check for existing bevel modifier
            for modifier in obj.modifiers:
                if modifier.type == 'BEVEL':
                    box = layout.box()
                    box.label(text="Bevel Modifier")
                    box.prop(modifier, "width")
                    box.prop(modifier, "segments")
                    box.prop(modifier, "profile")

            # Check for existing decimate modifier
            for modifier in obj.modifiers:
                if modifier.type == 'DECIMATE':
                    box = layout.box()
                    box.label(text="Decimate Modifier")
                    box.prop(modifier, "ratio")

# Utility function to get all mesh objects if none are selected
def get_target_objects(context):
    selected_objects = context.selected_objects
    if len(selected_objects) == 0:
        # If no objects are selected, return all mesh objects
        return [obj for obj in context.scene.objects if obj.type == 'MESH']
    return selected_objects

# Operator to Apply Shade Smooth to All Meshes
class OBJECT_OT_easy_shade_smooth(bpy.types.Operator):
    bl_label = "Shade Smooth"
    bl_idname = "object.easy_shade_smooth"
    bl_description = "Applies Shade Smooth to all selected mesh objects. If no objects are selected, applies to all mesh objects. Optionally enables Auto Smooth with a custom angle."

    def execute(self, context):
        props = context.scene.easy_utils_props
        target_objects = get_target_objects(context)
        
        for obj in target_objects:
            if obj.type == 'MESH':
                obj.select_set(True)
                bpy.context.view_layer.objects.active = obj
                
                # Apply Shade Smooth
                bpy.ops.object.shade_smooth()

                # Optionally enable Auto Smooth and set the Auto Smooth Angle
                if props.enable_auto_smooth:
                    obj.data.use_auto_smooth = True
                    # Convert the Auto Smooth Angle to radians
                    obj.data.auto_smooth_angle = math.radians(props.auto_smooth_angle)

                obj.select_set(False)

        self.report({'INFO'}, "Shade Smooth applied to selected/all mesh objects.")
        return {'FINISHED'}

# Operator to Perform Smart UV Unwrap on All Meshes
class OBJECT_OT_easy_smart_uv_unwrap(bpy.types.Operator):
    bl_label = "Smart UV Unwrap"
    bl_idname = "object.easy_smart_uv_unwrap"
    bl_description = "Performs a Smart UV Unwrap on all selected mesh objects. If no objects are selected, applies to all mesh objects. Supports an adjustable island margin."

    def execute(self, context):
        props = context.scene.easy_utils_props
        island_margin = props.island_margin
        target_objects = get_target_objects(context)
        
        for obj in target_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.uv.smart_project(island_margin=island_margin)
                bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, f"Smart UV Unwrap applied with {island_margin} margin.")
        return {'FINISHED'}

# Operator to Auto-Rename Meshes and Objects
class OBJECT_OT_easy_auto_rename(bpy.types.Operator):
    bl_label = "Auto Rename Objects and Meshes"
    bl_idname = "object.easy_auto_rename"
    bl_description = "Automatically renames all mesh objects and their meshes using a custom prefix. If no objects are selected, applies to all mesh objects."

    def execute(self, context):
        props = context.scene.easy_utils_props
        rename_prefix = props.rename_prefix
        
        n = 1
        target_objects = get_target_objects(context)
        sorted_objects = sorted(target_objects, key=lambda obj: obj.location.z, reverse=True)
        
        for obj in sorted_objects:
            if obj.type == 'MESH':
                obj.name = f"{rename_prefix}{n}"
                obj.data.name = f"{rename_prefix}{n}"
                n += 1

        self.report({'INFO'}, "Objects and meshes renamed successfully.")
        return {'FINISHED'}

# --- EasyOps Section ---

# Bevel operator
class OBJECT_OT_easy_bevel(bpy.types.Operator):
    bl_label = "Bevel"
    bl_idname = "object.easy_bevel"
    bl_description = "Adds a bevel modifier with default settings."

    def execute(self, context):
        target_objects = get_target_objects(context)
        for obj in target_objects:
            if obj.type == 'MESH':
                # Check if there's already a Bevel modifier
                if not any(mod.type == 'BEVEL' for mod in obj.modifiers):
                    modifier = obj.modifiers.new(name="Bevel", type='BEVEL')
                    modifier.width = 0.02
                    modifier.segments = 3
                    modifier.profile = 0.7
        self.report({'INFO'}, "Bevel applied to selected/all mesh objects.")
        return {'FINISHED'}

def turn_into_wireframe(obj):
    # Set the object to display as wireframe in the viewport
    obj.display_type = 'WIRE'
    
    # Check if the collection 'EASYOPS_CUTS' exists, if not, create it
    if "EASYOPS_CUTS" not in bpy.data.collections:
        new_collection = bpy.data.collections.new("EASYOPS_CUTS")
        bpy.context.scene.collection.children.link(new_collection)

    # Get the EASYOPS_CUTS collection
    cuts_collection = bpy.data.collections["EASYOPS_CUTS"]

    # If the object is already in a collection, unlink it from the original collection
    for collection in obj.users_collection:
        collection.objects.unlink(obj)

    # Link the object to the 'EASYOPS_CUTS' collection
    cuts_collection.objects.link(obj)


# Boolean operations
class OBJECT_OT_easy_boolean_difference(bpy.types.Operator):
    bl_label = "Boolean Difference"
    bl_idname = "object.easy_boolean_difference"
    bl_description = "Performs a Boolean Difference operation with the active object."

    def execute(self, context):
        target_objects = get_target_objects(context)
        active_obj = context.view_layer.objects.active
        
        for obj in target_objects:
            if obj.type == 'MESH' and obj != active_obj:
                modifier = obj.modifiers.new(name="Boolean Difference", type='BOOLEAN')
                modifier.operation = 'DIFFERENCE'
                modifier.object = active_obj

        turn_into_wireframe(active_obj)

        self.report({'INFO'}, "Boolean Difference applied.")
        return {'FINISHED'}

    
class OBJECT_OT_easy_boolean_union(bpy.types.Operator):
    bl_label = "Boolean Union"
    bl_idname = "object.easy_boolean_union"
    bl_description = "Performs a Boolean Union operation with the active object."

    def execute(self, context):
        target_objects = get_target_objects(context)
        active_obj = context.view_layer.objects.active
        
        for obj in target_objects:
            if obj.type == 'MESH' and obj != active_obj:
                modifier = obj.modifiers.new(name="Boolean Union", type='BOOLEAN')
                modifier.operation = 'UNION'
                modifier.object = active_obj

        turn_into_wireframe(active_obj)
        self.report({'INFO'}, "Boolean Union applied.")
        return {'FINISHED'}

class OBJECT_OT_easy_boolean_intersect(bpy.types.Operator):
    bl_label = "Boolean Intersect"
    bl_idname = "object.easy_boolean_intersect"
    bl_description = "Performs a Boolean Intersect operation with the active object."

    def execute(self, context):
        target_objects = get_target_objects(context)
        active_obj = context.view_layer.objects.active
        
        for obj in target_objects:
            if obj.type == 'MESH' and obj != active_obj:
                modifier = obj.modifiers.new(name="Boolean Intersect", type='BOOLEAN')
                modifier.operation = 'INTERSECT'
                modifier.object = active_obj

        turn_into_wireframe(active_obj)
        self.report({'INFO'}, "Boolean Intersect applied.")
        return {'FINISHED'}
    
#---
# Smart Apply for Boolean Modifiers
def smart_apply(obj):
    # Apply all boolean modifiers but leave other modifiers intact
    for modifier in obj.modifiers:
        if modifier.type == 'BOOLEAN':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=modifier.name)

class OBJECT_OT_easy_smart_apply(bpy.types.Operator):
    bl_label = "Smart Apply"
    bl_idname = "object.easy_smart_apply"
    bl_description = "Applies all boolean modifiers on the selected object but preserves other modifiers."

    def execute(self, context):
        target_objects = get_target_objects(context)

        for obj in target_objects:
            if obj.type == 'MESH':
                smart_apply(obj)  # Call the smart apply function
        
        self.report({'INFO'}, "Smart Apply completed for boolean modifiers.")
        return {'FINISHED'}


# Smart Decimate operator
class OBJECT_OT_easy_smart_decimate(bpy.types.Operator):
    bl_label = "Smart Decimate"
    bl_idname = "object.easy_smart_decimate"
    bl_description = "Adds a decimate modifier to reduce the polygon count."

    def execute(self, context):
        target_objects = get_target_objects(context)
        for obj in target_objects:
            if obj.type == 'MESH':
                # Check if there's already a Decimate modifier
                if not any(mod.type == 'DECIMATE' for mod in obj.modifiers):
                    modifier = obj.modifiers.new(name="Decimate", type='DECIMATE')
                    modifier.ratio = 0.5  # Adjust reduction factor

            
        self.report({'INFO'}, "Decimate applied to reduce polygon count.")
        return {'FINISHED'}

# Sharpen edges operator
class OBJECT_OT_easy_sharpen_edges(bpy.types.Operator):
    bl_label = "Sharpen Edges"
    bl_idname = "object.easy_sharpen_edges"
    bl_description = "Marks selected edges as sharp / equivalent to flat shading."

    def execute(self, context):
        target_objects = get_target_objects(context)
        for obj in target_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.mark_sharp()
        self.report({'INFO'}, "Sharp edges marked on selected/all objects.")
        return {'FINISHED'}

# Clean geometry operator
class OBJECT_OT_easy_clean_geometry(bpy.types.Operator):
    bl_label = "Clean Geometry"
    bl_idname = "object.easy_clean_geometry"
    bl_description = "Cleans loose geometry, removes doubles (merges vertices by distance), and dissolves degenerate faces."

    def execute(self, context):
        target_objects = get_target_objects(context)
        for obj in target_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')

                # Merge by Distance (Replacing remove_doubles)
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.merge_by_distance(distance=0.0001)  # Correct distance operator

                # Delete loose geometry
                bpy.ops.mesh.delete_loose()

                # Dissolve degenerate geometry
                bpy.ops.mesh.dissolve_degenerate()

                bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, "Cleaned geometry on selected/all objects.")
        return {'FINISHED'}


# Operator to Remove Doubles (Merge by Distance) on All Meshes
class OBJECT_OT_easy_remove_doubles(bpy.types.Operator):
    bl_label = "Remove Doubles (Merge by Distance)"
    bl_idname = "object.easy_remove_doubles"
    bl_description = "Removes doubles by merging vertices by distance for all selected mesh objects. If no objects are selected, applies to all mesh objects."

    def execute(self, context):
        target_objects = get_target_objects(context)
        for obj in target_objects:
            if obj.type == 'MESH':
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.remove_doubles()
                bpy.ops.object.mode_set(mode='OBJECT')

        self.report({'INFO'}, "Doubles removed from selected/all mesh objects.")
        return {'FINISHED'}


# Register and Unregister Classes
classes = [
    EasyUtilsProperties,
    EasyUtilsPanel,
    EasyOpsPanel,
    OBJECT_OT_easy_auto_rename,
    OBJECT_OT_easy_smart_uv_unwrap,
    OBJECT_OT_easy_shade_smooth,
    OBJECT_OT_easy_remove_doubles,
    OBJECT_OT_easy_bevel,
    OBJECT_OT_easy_boolean_difference,
    OBJECT_OT_easy_boolean_union,
    OBJECT_OT_easy_boolean_intersect,
    OBJECT_OT_easy_smart_decimate,
    OBJECT_OT_easy_sharpen_edges,
    OBJECT_OT_easy_clean_geometry,
    OBJECT_OT_easy_smart_apply,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.easy_utils_props = bpy.props.PointerProperty(type=EasyUtilsProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.easy_utils_props

if __name__ == "__main__":
    register()

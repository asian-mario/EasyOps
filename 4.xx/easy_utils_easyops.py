bl_info = {
    "name": "Easy Utils & EasyOps",
    "author": "asianmario",
    "version": (1, 1, 0),
    "blender": (4, 4, 0),
    "location": "View3D > Sidebar > Easy Utils",
    "description": "A collection of modelling and cleanup utilities",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object",
}

import bpy
import random
import bmesh
import math
from bpy.props import (
    StringProperty,
    FloatProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)


# -------------------------------------------------------------------
#    Properties
# -------------------------------------------------------------------

class EasyUtilsProperties(bpy.types.PropertyGroup):
    rename_prefix: StringProperty(
        name="Rename Prefix",
        description="Prefix for auto-renaming objects and meshes",
        default="EO-"
    )
    island_margin: FloatProperty(
        name="Island Margin",
        description="Margin between UV islands for Smart UV Unwrap",
        default=0.02,
        min=0.0,
        max=1.0
    )
    enable_auto_smooth: BoolProperty(
        name="Enable Auto Smooth",
        description="Enable Auto Smooth after applying Shade Smooth",
        default=False
    )
    auto_smooth_angle: FloatProperty(
        name="Auto Smooth Angle",
        description="Angle for Auto Smooth (0 to 180 degrees)",
        default=30.0,
        min=0.0,
        max=180.0
    )
    metallic_color_min: FloatProperty(
        name="Metallic Min Intensity",
        description="Minimum greyscale for metallic materials",
        default=0.3,
        min=0.0,
        max=1.0
    )
    metallic_color_max: FloatProperty(
        name="Metallic Max Intensity",
        description="Maximum greyscale for metallic materials",
        default=1.0,
        min=0.0,
        max=1.0
    )


# -------------------------------------------------------------------
#    Utility functions
# -------------------------------------------------------------------

def get_target_objects(context):
    objs = context.selected_objects
    if not objs:
        return [o for o in context.scene.objects if o.type == 'MESH']
    return objs

def turn_into_wireframe(obj):
    obj.display_type = 'WIRE'
    # Ensure collection exists
    if "EASYOPS_CUTS" not in bpy.data.collections:
        col = bpy.data.collections.new("EASYOPS_CUTS")
        context = bpy.context
        context.scene.collection.children.link(col)
    cuts = bpy.data.collections["EASYOPS_CUTS"]
    # Move object into that collection
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    cuts.objects.link(obj)


# -------------------------------------------------------------------
#    Operators
# -------------------------------------------------------------------

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
        targets = get_target_objects(context)
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
        for obj in get_target_objects(context):
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
        for obj in get_target_objects(context):
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
        targets = sorted(get_target_objects(context),
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
        for obj in get_target_objects(context):
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
        for obj in get_target_objects(context):
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
        for obj in get_target_objects(context):
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
        for obj in get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Difference", 'BOOLEAN')
                mod.operation = 'DIFFERENCE'
                mod.object = active
        turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Difference applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_boolean_union(bpy.types.Operator):
    """Boolean Union"""
    bl_idname = "object.easy_boolean_union"
    bl_label = "Boolean Union"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.view_layer.objects.active
        for obj in get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Union", 'BOOLEAN')
                mod.operation = 'UNION'
                mod.object = active
        turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Union applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_boolean_intersect(bpy.types.Operator):
    """Boolean Intersect"""
    bl_idname = "object.easy_boolean_intersect"
    bl_label = "Boolean Intersect"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active = context.view_layer.objects.active
        for obj in get_target_objects(context):
            if obj.type == 'MESH' and obj is not active:
                mod = obj.modifiers.new("Boolean Intersect", 'BOOLEAN')
                mod.operation = 'INTERSECT'
                mod.object = active
        turn_into_wireframe(active)
        self.report({'INFO'}, "Boolean Intersect applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_smart_apply(bpy.types.Operator):
    """Apply only boolean modifiers"""
    bl_idname = "object.easy_smart_apply"
    bl_label = "Smart Apply"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in get_target_objects(context):
            if obj.type == 'MESH':
                for mod in list(obj.modifiers):
                    if mod.type == 'BOOLEAN':
                        context.view_layer.objects.active = obj
                        bpy.ops.object.modifier_apply(modifier=mod.name)
        self.report({'INFO'}, "Boolean modifiers applied.")
        return {'FINISHED'}


class OBJECT_OT_easy_smart_decimate(bpy.types.Operator):
    """Add Decimate modifier"""
    bl_idname = "object.easy_smart_decimate"
    bl_label = "Smart Decimate"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in get_target_objects(context):
            if obj.type == 'MESH' and not any(m.type=='DECIMATE' for m in obj.modifiers):
                mod = obj.modifiers.new("Decimate", 'DECIMATE')
                mod.ratio = 0.5
        self.report({'INFO'}, "Decimate modifier added.")
        return {'FINISHED'}


def detect_sharp_edges(obj, angle_threshold=30):
    thresh = math.radians(angle_threshold)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(obj.data)
    for e in bm.edges:
        if e.is_manifold and len(e.link_faces)==2:
            angle = e.link_faces[0].normal.angle(e.link_faces[1].normal)
            if angle > thresh:
                e.smooth = False
                e.seam = True
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.transform.edge_bevelweight(value=1.0)
    bpy.ops.transform.edge_crease(value=1.0)
    bpy.ops.object.mode_set(mode='OBJECT')

def apply_bevel_modifier(obj):
    bevel = next((m for m in obj.modifiers if m.type=='BEVEL'), None)
    if not bevel:
        bevel = obj.modifiers.new("Bevel", 'BEVEL')
    bevel.width = 0.02
    bevel.segments = 3
    bevel.limit_method = 'WEIGHT'

def enable_auto_smooth(obj, angle=30):
    obj.data.use_auto_smooth = True
    obj.data.auto_smooth_angle = math.radians(angle)

class OBJECT_OT_easy_ssharpen(bpy.types.Operator):
    """Smart Sharpen: detect, bevel & auto-smooth"""
    bl_idname = "object.easy_ssharpen"
    bl_label = "SSharpen"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for obj in get_target_objects(context):
            if obj.type == 'MESH':
                detect_sharp_edges(obj)
                apply_bevel_modifier(obj)
                enable_auto_smooth(obj)
        self.report({'INFO'}, "SSharpen complete.")
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


# -------------------------------------------------------------------
#    UI: Panels & Menus
# -------------------------------------------------------------------

class OBJECT_MT_easy_radial_menu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_easy_ops_radial_menu"
    bl_label = "EasyOps"

    def draw(self, context):
        pie = self.layout.menu_pie()
        sel = context.selected_objects

        if len(sel) == 1:
            pie.operator("object.easy_bevel",             icon='MOD_BEVEL')
            pie.operator("object.easy_sharpen_edges",     icon='MOD_SHRINKWRAP')
            pie.operator("object.easy_smart_apply",       icon='CHECKMARK')
            pie.operator("object.easy_smart_uv_unwrap",   icon='UV')
            pie.operator("object.easy_clean_geometry",    icon='CLEAN_CHANNELS')
            pie.operator("object.easy_remove_doubles",    icon='X')
            pie.operator("object.assign_random_materials",icon='MATERIAL')

        elif len(sel) >= 2:
            pie.operator("object.easy_boolean_difference",icon='MOD_BOOLEAN')
            pie.operator("object.easy_boolean_union",     icon='MOD_BOOLEAN')
            pie.operator("object.easy_boolean_intersect", icon='MOD_BOOLEAN')
            pie.operator("object.easy_smart_uv_unwrap",   icon='UV')

        else:
            pie.label(text="Select 1–2 meshes", icon='INFO')



addon_keymaps = []

def register_shortcut():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new("wm.call_menu_pie", 'Z', 'PRESS', shift=True)
        kmi.properties.name = OBJECT_MT_easy_radial_menu.bl_idname
        addon_keymaps.append((km, kmi))

def unregister_shortcut():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


class EasyUtilsPanel(bpy.types.Panel):
    """Easy Utils Tools"""
    bl_label = "Easy Utils"
    bl_idname = "OBJECT_PT_easy_utils"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Utils"

    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_utils_props

        layout.prop(props, "rename_prefix")
        layout.operator("object.easy_auto_rename")
        layout.separator()
        layout.operator("object.easy_ssharpen", text="SSharpen")
        layout.label(text="Random Materials:")
        layout.operator("object.assign_random_materials")
        layout.prop(props, "metallic_color_min")
        layout.prop(props, "metallic_color_max")

        layout.separator()
        layout.prop(props, "island_margin")
        layout.operator("object.easy_smart_uv_unwrap")
        layout.prop(props, "enable_auto_smooth")
        layout.prop(props, "auto_smooth_angle")
        layout.operator("object.easy_shade_smooth")
        layout.operator("object.easy_remove_doubles")


class EasyOpsPanel(bpy.types.Panel):
    """EasyOps Boolean & Cleanup"""
    bl_label = "EasyOps"
    bl_idname = "OBJECT_PT_easy_ops"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Utils"

    def draw(self, context):
        layout = self.layout
        obj = context.object

        layout.label(text="Bevel & Booleans")
        layout.operator("object.easy_bevel")
        layout.operator("object.easy_boolean_difference")
        layout.operator("object.easy_boolean_union")
        layout.operator("object.easy_boolean_intersect")
        layout.separator()
        layout.label(text="Modifiers & Cleanup")
        layout.operator("object.easy_smart_decimate")
        layout.operator("object.easy_sharpen_edges", text="Flat Shading")
        layout.operator("object.easy_clean_geometry")
        layout.operator("object.easy_smart_apply")

        if obj and obj.type=='MESH':
            layout.separator()
            layout.label(text="Modifier Controls")
            for m in obj.modifiers:
                if m.type=='BEVEL':
                    box = layout.box()
                    box.label(text="Bevel Modifier")
                    box.prop(m, "width")
                    box.prop(m, "segments")
                    box.prop(m, "profile")
                if m.type=='DECIMATE':
                    box = layout.box()
                    box.label(text="Decimate Modifier")
                    box.prop(m, "ratio")


# -------------------------------------------------------------------
#    Registration
# -------------------------------------------------------------------

classes = [
    EasyUtilsProperties,
    OBJECT_OT_easy_random_materials,
    OBJECT_OT_easy_shade_smooth,
    OBJECT_OT_easy_smart_uv_unwrap,
    OBJECT_OT_easy_auto_rename,
    OBJECT_OT_easy_remove_doubles,
    OBJECT_OT_easy_clean_geometry,
    OBJECT_OT_easy_bevel,
    OBJECT_OT_easy_boolean_difference,
    OBJECT_OT_easy_boolean_union,
    OBJECT_OT_easy_boolean_intersect,
    OBJECT_OT_easy_smart_apply,
    OBJECT_OT_easy_smart_decimate,
    OBJECT_OT_easy_sharpen_edges,
    OBJECT_OT_easy_ssharpen,
    OBJECT_MT_easy_radial_menu,
    EasyUtilsPanel,
    EasyOpsPanel,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.easy_utils_props = PointerProperty(type=EasyUtilsProperties)
    register_shortcut()

def unregister():
    unregister_shortcut()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.easy_utils_props

if __name__ == "__main__":
    register()

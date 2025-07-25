bl_info = {
    "name": "Easy Utils & EasyOps",
    "author": "asianmario",
    "version": (0, 1, 3),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Easy Utils",
    "description": "A collection of modelling and cleanup utilities",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object",
}

import bpy
from bpy.props import PointerProperty

from . import properties
from . import operators
from . import ui

classes = [
    properties.EasyUtilsProperties,
    operators.OBJECT_OT_easy_random_materials,
    operators.OBJECT_OT_easy_shade_smooth,
    operators.OBJECT_OT_easy_smart_uv_unwrap,
    operators.OBJECT_OT_easy_auto_rename,
    operators.OBJECT_OT_easy_remove_doubles,
    operators.OBJECT_OT_easy_clean_geometry,
    operators.OBJECT_OT_easy_bevel,
    operators.OBJECT_OT_easy_boolean_difference,
    operators.OBJECT_OT_easy_boolean_union,
    operators.OBJECT_OT_easy_boolean_intersect,
    operators.OBJECT_OT_easy_smart_apply,
    operators.OBJECT_OT_easy_smart_decimate,
    operators.OBJECT_OT_easy_sharpen_edges,
    operators.OBJECT_OT_easy_ssharpen,
    operators.OBJECT_OT_easy_freeform_boolean,
    ui.OBJECT_MT_easy_radial_menu,
    ui.EasyUtilsPanel,
    ui.EasyOpsPanel,
]

addon_keymaps = []

def register_shortcut():
    kc = bpy.context.window_manager.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Object Mode', space_type='EMPTY')
        kmi = km.keymap_items.new("wm.call_menu_pie", 'Z', 'PRESS', shift=True)
        kmi.properties.name = ui.OBJECT_MT_easy_radial_menu.bl_idname
        addon_keymaps.append((km, kmi))

def unregister_shortcut():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.easy_utils_props = PointerProperty(type=properties.EasyUtilsProperties)
    register_shortcut()

def unregister():
    unregister_shortcut()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.easy_utils_props

if __name__ == "__main__":
    register()
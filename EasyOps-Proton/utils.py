import bpy
import bmesh
import math


def get_target_objects(context):
    """Get selected objects or all mesh objects if none selected"""
    objs = context.selected_objects
    if not objs:
        return [o for o in context.scene.objects if o.type == 'MESH']
    return objs


def turn_into_wireframe(obj):
    """Turn object into wireframe and move to EASYOPS_CUTS collection"""
    obj.display_type = 'WIRE'
    # Ensure collection exists
    if "EASYOPS_CUTS" not in bpy.data.collections:
        col = bpy.data.collections.new("EASYOPS_CUTS")
        # Get current context
        bpy.context.scene.collection.children.link(col)
    cuts = bpy.data.collections["EASYOPS_CUTS"]
    # Move object into that collection
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    cuts.objects.link(obj)


def detect_sharp_edges(obj, angle_threshold=30):
    """Detect and mark sharp edges based on angle threshold"""
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
    """Apply or create a bevel modifier with weight limit"""
    bevel = next((m for m in obj.modifiers if m.type=='BEVEL'), None)
    if not bevel:
        bevel = obj.modifiers.new("Bevel", 'BEVEL')
    bevel.width = 0.02
    bevel.segments = 3
    bevel.limit_method = 'WEIGHT'


def enable_auto_smooth(obj, angle=30):
    """Enable auto smooth on object with specified angle"""
    obj.data.use_auto_smooth = True
    obj.data.auto_smooth_angle = math.radians(angle)

def is_surface_drawing_enabled(context):
    return hasattr(context.scene, 'easy_utils_props') and context.scene.easy_utils_props.surface_drawing_mode

def recalculate_normals_for_objects(context, objects):
    if not objects:
        return
    
    original_active = context.view_layer.objects.active
    original_mode = context.mode

    try:
        for obj in objects:
            if obj.type == 'MESH':
                context.view_layer.objects.active = obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.normals_make_consistent(inside=False)
                bpy.ops.object.mode_set(mode='OBJECT')
    
    finally:
        context.view_layer.objects.active = original_active
        if original_mode != 'OBJECT':
            try:
                bpy.ops.object.mode_set(mode=original_mode.replace('_','').lower())
            except:
                pass

def smart_apply_modifiers(obj):
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
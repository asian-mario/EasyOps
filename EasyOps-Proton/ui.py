import bpy


class OBJECT_MT_easy_radial_menu(bpy.types.Menu):
    bl_idname = "OBJECT_MT_easy_ops_radial_menu"
    bl_label = "EasyOps"

    def draw(self, context):
        pie = self.layout.menu_pie()
        sel = context.selected_objects

        if len(sel) == 1:
            pie.operator("object.easy_bevel",             icon='MOD_BEVEL')
            pie.operator("object.easy_ssharpen",     icon='MOD_SHRINKWRAP')
            pie.operator("object.easy_smart_apply",       icon='CHECKMARK')
            ff_op = pie.operator("object.easy_freeform_boolean", text="FreeForm", icon='GREASEPENCIL')
            pie.operator("object.easy_smart_uv_unwrap",   icon='UV') 
            # These currently do not load. I will check the iconpacks.
            pie.operator("object.easy_clean_geometry",    icon='BRUSH_DATA')
            pie.operator("object.easy_remove_doubles",    icon='X')
            pie.operator("object.assign_random_materials",icon='MATERIAL')
            
            ff_op.operation = 'DIFFERENCE'

        elif len(sel) >= 2:
            pie.operator("object.easy_boolean_difference",icon='MOD_BOOLEAN')
            pie.operator("object.easy_boolean_union",     icon='MOD_BOOLEAN')
            pie.operator("object.easy_boolean_intersect", icon='MOD_BOOLEAN')
            pie.operator("object.easy_smart_uv_unwrap",   icon='UV')
            ff_op = pie.operator("object.easy_freeform_boolean", text="FreeForm Diff", icon='SELECT_SUBTRACT')
            ff_op.operation = 'DIFFERENCE'

        else:
            pie.label(text="Select 1–2 meshes", icon='INFO')

class EasyUtilsPanel(bpy.types.Panel):
    """Easy Utils Tools"""
    bl_label = "EasyUtils"
    bl_idname = "OBJECT_PT_easy_utils"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Utils"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='TOOL_SETTINGS')
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_utils_props

        main_col = layout.column(align=True)

        # Naming
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="Auto Naming", icon="OUTLINER_DATA_FONT")

        col = box.column(align=True)
        col.scale_y = 0.9

        row = col.row(align=True)
        row.prop(props, "rename_prefix", text="")
        row.operator("object.easy_auto_rename", text ="", icon='FILE_REFRESH')

        # Shading
        main_col.separator(factor=0.5)
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="Surface Control", icon='SHADING_RENDERED')
        
        col = box.column(align=True)
        col.scale_y = 1.1

        # Shading Controls
        row = col.row(align=True)
        row.operator("object.easy_ssharpen", text="SSharpen", icon='MOD_SMOOTH')
        row.operator("object.easy_shade_smooth", text="Smooth", icon='SURFACE_NSURFACE')

        # Materials
        main_col.separator(factor=0.5)
        vox = main_col.box()
        header = box.row(align=True)
        header.label(text="Materials", icon='MATERIAL')

        col = box.column(align=True)
        col.scale_y = 1.0

        col.operator("Object.assign_random_materials", text="Random Materials", icon='MATERIAL')

        # Material Settings
        sub_box = col.box()
        sub_col = sub_box.column(align=True)
        sub_col.scale_y = 0.8
        sub_col.prop(props, "metallic_color_min", text="Min")
        sub_col.prop(props, "metallic_color_max", text="Max")

        # UV Mapping
        main_col.separator(factor=0.5)
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="UV Mapping", icon='UV')

        """
            song rec. of the commit: fake plastic trees
        """

        col = box.column(align=True)
        col.scale_y = 1.0

        # UV controls
        row = col.row(align=True)
        row.prop(props, "island_margin", text="Margin")

        col.operator("object.easy_smart_uv_unwrap", text="Smart UV Unwrap", icon='UV')

        # Cleanup
        main_col.separator(factor=0.5)
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="Cleanup", icon='BRUSH_DATA')

        col = box.column(align=True)
        col.scale_y = 1.1
        col.operator("object.easy_remove_doubles", text="Remove Doubles", icon='X')

class EasyOpsPanel(bpy.types.Panel):
    """EasyOps Boolean & Cleanup"""
    bl_label = "EasyOps"
    bl_idname = "OBJECT_PT_easy_ops"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Utils"

    def draw_header(self, context):
        layout = self.layout
        layout.label(text="", icon='MOD_BOOLEAN')
    
    def draw(self, context):
        layout = self.layout
        obj = context.object

        # Main Container
        main_col = layout.column(align=True)

        # Bevel
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="Bevel", icon="MOD_BEVEL")

        col = box.column(align=True)
        col.scale_y = 1.2
        col.operator("object.easy_bevel", text="Add Bevel", icon='MOD_BEVEL')

        # Boolean Operations
        main_col.separator(factor=0.5)
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="Boolean Operations", icon='MOD_BOOLEAN')

        col = box.column(align=True)
        col.scale_y = 1.1

        # Booleans
        row = col.row(align=True)
        row.operator("object.easy_boolean_difference", text="Diff", icon='SELECT_SUBTRACT')
        row.operator("object.easy_boolean_union", text="Union", icon='SELECT_EXTEND')
        row.operator("object.easy_boolean_intersect", text="Int", icon='SELECT_INTERSECT')

        # Freeform Booleans
        main_col.separator(factor=0.3)
        ff_box = main_col.box()
        ff_header = ff_box.row(align=True)
        ff_header.label(text="FreeForm Boolean", icon='GREASEPENCIL')

        ff_col = ff_box.column(align=True)
        ff_col.scale_y = 1.0

        # FreeForm Operations
        ff_row = ff_col.row(align=True)

        op = ff_row.operator("object.easy_freeform_boolean", text="FF-", icon='SELECT_SUBTRACT')
        op.operation = 'DIFFERENCE'

        op = ff_row.operator("object.easy_freeform_boolean", text="FF+", icon='SELECT_EXTEND')
        op.operation = 'UNION'

        op = ff_row.operator("object.easy_freeform_boolean", text="FF∩", icon='SELECT_INTERSECT')
        op.operation = 'INTERSECT'

        # Template Booleans
        tb_col = ff_box.column(align=True)
        tb_col.scale_y = 1.0

        tb_row = tb_col.row(align=True)
        op = tb_row.operator("object.easy_rectangle_boolean", text="◰-", icon='SELECT_SUBTRACT')
        op.operation = 'DIFFERENCE'
    

        # Modelling Tools
        main_col.separator(factor=0.5)
        box = main_col.box()
        header = box.row(align=True)
        header.label(text="Modelling Tools", icon='EDITMODE_HLT')

        col = box.column(align=True)
        col.scale_y = 1.0

        row = col.row(align=True)
        row.operator("object.easy_smart_decimate", text="Decimate", icon='MOD_DECIM')
        row.operator("object.easy_clean_geometry", text="Clean", icon='BRUSH_DATA')

        row = col.row(align=True)
        row.operator("object.easy_smart_sharpen_edges", text="Flat Shade", icon='MESH_DATA')
        row.operator("object.easy_smart_smart_apply", text="Smart Apply", icon='CHECKMARK')

        # Active Modifiers
        if obj and obj.type == 'MESH' and obj.modifiers:
            main_col.separator(factor=0.5)
            mod_box = main_col.box()
            mod_header = mod_box.row(align=True)
            mod_header.label(text="Active Modifiers", icon='MODIFIER')

            for m in obj.modifiers:
                if m.type == 'BEVEL':
                    self.draw_bevel_modifier(mod_box, m)
                elif m.type == 'DECIMATE':
                    self.draw_decimate_modifier(mod_box, m)
    
    """Im doing this entire commit on a friday so i'm lazy. Will comment later"""

    def draw_bevel_modifier(self, layout, modifier):
            box = layout.box()

            header = box.row(align=True)
            header.prop(modifier, "show_viewport", text="", icon='RESTRICT_VIEW_OFF' if modifier.show_viewport else 'RESTRICT_VIEW_ON')
            header.label(text=f"Bevel: {modifier.name}", icon='MOD_BEVEL')

            col = box.column(align=True)
            col.scale_y = 0.9

            row = col.row(align=True)
            row.prop(modifier, "width", text="Width")
            row.prop(modifier, "segments", text="Seg")

            col.prop(modifier, "profile", text="Profile", slider=True)

    def draw_decimate_modifier(self, layout, modifier):
        box = layout.box()

        header = box.row(align=True)
        header.prop(modifier, "show_viewport", text="", icon='RESTRICT_VIEW_OFF' if modifier.show_viewport else 'RESTRICT_VIEW_ON')
        header.label(text=f"Decimate: {modifier.name}", icon='MOD_DECIM')

        col = box.column(align=True)
        col.scale_y = 0.9
        col.prop(modifier, "ratio", text="Ratio", slider=True)

# TODO: Status and Info
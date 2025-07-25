import bpy


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
        
        """
        Deprecated
        layout.prop(props, "enable_auto_smooth")
        layout.prop(props, "auto_smooth_angle")
        """
        
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
        
        # Add FreeForm Boolean section
        layout.separator()
        layout.label(text="FreeForm Boolean")
        box = layout.box()
        col = box.column(align=True)
        
        # Create a row for the operation buttons
        row = col.row(align=True)
        
        # FreeForm Difference
        op = row.operator("object.easy_freeform_boolean", text="FF Diff", icon='SELECT_SUBTRACT')
        op.operation = 'DIFFERENCE'
        
        # FreeForm Union  
        op = row.operator("object.easy_freeform_boolean", text="FF Union", icon='SELECT_EXTEND')
        op.operation = 'UNION'
        
        # FreeForm Intersect
        op = row.operator("object.easy_freeform_boolean", text="FF Intersect", icon='SELECT_INTERSECT')
        op.operation = 'INTERSECT'
        
        # Settings row
        props_row = col.row(align=True)
        props_row.label(text="Depth:")
        # We can't directly access operator properties here, so we'll add scene properties
        
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
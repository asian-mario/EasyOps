import bpy
import os

bl_info = {
    "name": "EasyScripts",
    "blender": (2, 93, 0),
    "category": "Object",
}

# Directory to store user scripts
SCRIPTS_DIR = os.path.join(bpy.utils.resource_path('USER'), "easy_scripts")

# Ensure the scripts directory exists
if not os.path.exists(SCRIPTS_DIR):
    os.makedirs(SCRIPTS_DIR)

# Custom Properties for EasyScripts
class EasyScriptsProperties(bpy.types.PropertyGroup):
    # Property for storing the current script name
    current_script_name: bpy.props.StringProperty(
        name="Script Name",
        description="Name of the script",
        default="NewScript"
    )
    
    # Property for file upload path
    script_upload: bpy.props.StringProperty(
        name="Script File",
        description="Load a script from your file system",
        default="",
        subtype='FILE_PATH'
    )

    # Property to list saved scripts in a dropdown
    saved_scripts: bpy.props.EnumProperty(
        name="Saved Scripts",
        description="List of saved scripts",
        items=lambda self, context: [(f, f, "") for f in os.listdir(SCRIPTS_DIR) if f.endswith('.py')],
        default=None
    )

# Operator for writing and saving scripts using Text blocks (Text Editor)
class OBJECT_OT_easy_save_script(bpy.types.Operator):
    bl_label = "Save Script"
    bl_idname = "object.easy_save_script"
    bl_description = "Saves the current text block script to disk"
    
    def execute(self, context):
        props = context.scene.easy_scripts_props
        # Get the currently active text block
        text_block = bpy.data.texts.get(context.space_data.text.name) if context.space_data.type == 'TEXT_EDITOR' else None

        if not text_block:
            self.report({'ERROR'}, "No active text block to save.")
            return {'CANCELLED'}

        # Ensure the script name is valid
        if not props.current_script_name:
            self.report({'ERROR'}, "Script name cannot be empty.")
            return {'CANCELLED'}

        # Create script path
        script_path = os.path.join(SCRIPTS_DIR, f"{props.current_script_name}.py")
        
        # Save the text block content to the script path
        try:
            with open(script_path, 'w') as script_file:
                script_file.write(text_block.as_string())
            self.report({'INFO'}, f"Script '{props.current_script_name}.py' saved.")
        except Exception as e:
            self.report({'ERROR'}, f"Error saving script: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

# Operator for uploading a script and saving it to the SCRIPTS_DIR without loading into the Text Editor
class OBJECT_OT_easy_upload_script(bpy.types.Operator):
    bl_label = "Upload Script"
    bl_idname = "object.easy_upload_script"
    bl_description = "Uploads a script from the selected file and saves it to the EasyScripts directory without loading"

    def execute(self, context):
        props = context.scene.easy_scripts_props
        script_path = props.script_upload
        
        # Check if the file exists
        if not os.path.exists(script_path):
            self.report({'ERROR'}, "File not found.")
            return {'CANCELLED'}
        
        # Create a destination path in the SCRIPTS_DIR
        script_name = os.path.basename(script_path)  # Extract just the filename
        destination_path = os.path.join(SCRIPTS_DIR, script_name)

        # Copy the script to the EasyScripts directory
        try:
            with open(script_path, 'r') as src_file:
                content = src_file.read()
            with open(destination_path, 'w') as dest_file:
                dest_file.write(content)
            self.report({'INFO'}, f"Script '{script_name}' uploaded and saved to EasyScripts directory.")
        except Exception as e:
            self.report({'ERROR'}, f"Error uploading script: {str(e)}")
            return {'CANCELLED'}
        
        # Refresh the saved scripts list
        bpy.context.scene.easy_scripts_props.saved_scripts = None
        
        return {'FINISHED'}

# Operator for running a selected script from the dropdown list (3D Viewport)
class OBJECT_OT_easy_run_script(bpy.types.Operator):
    bl_label = "Run Script"
    bl_idname = "object.easy_run_script"
    bl_description = "Runs the selected script from the saved scripts dropdown"
    
    def execute(self, context):
        props = context.scene.easy_scripts_props
        script_path = os.path.join(SCRIPTS_DIR, props.saved_scripts)
        
        # Execute the script
        try:
            exec(compile(open(script_path).read(), script_path, 'exec'))
            self.report({'INFO'}, f"Script '{props.saved_scripts}' executed.")
        except Exception as e:
            self.report({'ERROR'}, f"Error running script: {str(e)}")
        
        return {'FINISHED'}

# Operator for removing a selected script from the list and disk
class OBJECT_OT_easy_remove_script(bpy.types.Operator):
    bl_label = "Remove Script"
    bl_idname = "object.easy_remove_script"
    bl_description = "Removes the selected script from the saved list and deletes the file"
    
    def execute(self, context):
        props = context.scene.easy_scripts_props
        script_path = os.path.join(SCRIPTS_DIR, props.saved_scripts)
        
        # Remove the file
        try:
            os.remove(script_path)
            self.report({'INFO'}, f"Script '{props.saved_scripts}' removed.")
        except Exception as e:
            self.report({'ERROR'}, f"Error removing script: {str(e)}")
            return {'CANCELLED'}
        
        # Refresh the saved scripts list
        bpy.context.scene.easy_scripts_props.saved_scripts = None
        
        return {'FINISHED'}

# Operator for editing a script by loading it into the Text Editor
class OBJECT_OT_easy_edit_script(bpy.types.Operator):
    bl_label = "Edit Script"
    bl_idname = "object.easy_edit_script"
    bl_description = "Loads the selected script into the Text Editor for editing"

    def execute(self, context):
        props = context.scene.easy_scripts_props
        script_path = os.path.join(SCRIPTS_DIR, props.saved_scripts)

        # Check if the file exists
        if not os.path.exists(script_path):
            self.report({'ERROR'}, "Script not found.")
            return {'CANCELLED'}

        # Load the script into a new text block
        try:
            bpy.data.texts.load(script_path)
            self.report({'INFO'}, f"Script '{props.saved_scripts}' loaded into the Text Editor for editing.")
        except Exception as e:
            self.report({'ERROR'}, f"Error loading script: {str(e)}")
            return {'CANCELLED'}
        
        return {'FINISHED'}

# Panel for saving scripts in the Text Editor
class EasyScriptsTextEditorPanel(bpy.types.Panel):
    bl_label = "Easy Scripts (Text Editor)"
    bl_idname = "TEXT_PT_easy_scripts_text_editor"
    bl_space_type = 'TEXT_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Easy Scripts"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_scripts_props
        
        # Script writing section (Script Editor)
        layout.label(text="Write Script (via Text Editor)")
        layout.prop(props, "current_script_name")
        layout.operator("object.easy_save_script", text="Save Script")

# Panel for managing scripts in the 3D Viewport
class EasyScripts3DViewPanel(bpy.types.Panel):
    bl_label = "Easy Scripts (3D Viewport)"
    bl_idname = "VIEW3D_PT_easy_scripts_3d_view"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Easy Scripts"
    
    def draw(self, context):
        layout = self.layout
        props = context.scene.easy_scripts_props
        
        # File upload section
        layout.label(text="Upload Script from File")
        layout.prop(props, "script_upload", text="")
        layout.operator("object.easy_upload_script", text="Upload Script")
        
        layout.separator()
        
        # Saved scripts dropdown and actions (run, edit, remove)
        layout.label(text="Saved Scripts")
        layout.prop(props, "saved_scripts", text="")  # Dropdown list of saved scripts
        layout.operator("object.easy_run_script", text="Run Script")
        layout.operator("object.easy_edit_script", text="Edit Script")
        layout.operator("object.easy_remove_script", text="Remove Script")

# Registering all classes
classes = [
    EasyScriptsProperties,
    EasyScriptsTextEditorPanel,
    EasyScripts3DViewPanel,
    OBJECT_OT_easy_save_script,
    OBJECT_OT_easy_upload_script,
    OBJECT_OT_easy_run_script,
    OBJECT_OT_easy_remove_script,
    OBJECT_OT_easy_edit_script,
]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.easy_scripts_props = bpy.props.PointerProperty(type=EasyScriptsProperties)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.easy_scripts_props

if __name__ == "__main__":
    register()

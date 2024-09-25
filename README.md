
# EasyUtils & EasyOps for Blender 2.93+

**EasyUtils & EasyOps** is a Blender add-on that provides a set of tools designed to make common mesh operations easier and faster. This includes auto-renaming, UV unwrapping, smart apply operations, booleans with automatic wireframe mode, geometry cleaning, and more. All boolean effectors are automatically moved to a dedicated collection called `EASYOPS_CUTS`.

## Features
- **Auto Rename**: Automatically renames selected or all mesh objects and their mesh data with a custom prefix.
- **Smart UV Unwrap**: Quickly performs a smart UV unwrap with customizable island margins.
- **Shade Smooth & Auto Smooth**: Applies smooth shading to selected or all objects with an option to enable auto smooth and set a custom smooth angle.
- **Bevel Modifier**: Quickly adds a bevel modifier to selected objects.
- **Smart Decimate**: Adds a decimate modifier to reduce polygon count.
- **Boolean Operations**: Perform boolean operations (Difference, Union, Intersect) with active objects automatically converted to wireframe and moved to a custom collection (`EASYOPS_CUTS`).
- **Flat Shading**: Apply flat shading to selected or all objects.
- **Clean Geometry**: Cleans up geometry by removing doubles, deleting loose elements, and dissolving degenerate geometry.
- **Smart Apply**: Applies only the boolean modifiers on objects while preserving other modifiers.

## Installation
1. Download the `easy_utils_easyops.py` script.
2. Open Blender and go to **Edit > Preferences > Add-ons**.
3. Click **Install** in the top right and navigate to the downloaded `.py` file.
4. Select the file and click **Install Add-on**.
5. Once installed, enable the add-on by checking the box next to its name.

## Usage
The add-on creates a new tab in the **3D Viewport** called **Easy Utils**. It contains two sections: **Easy Utils** and **EasyOps**.

### Easy Utils Panel
1. **Auto Rename**: Automatically renames selected or all mesh objects and their mesh data using the provided prefix.
    - **Prefix**: Set the prefix for renaming (e.g., `AK-`).
    - **Usage**: Select objects, set the prefix, and click `Auto Rename`.
    
2. **Smart UV Unwrap**: Quickly unwraps the selected or all mesh objects with adjustable island margins.
    - **Island Margin**: Adjust the distance between UV islands (default: `0.02`).
    - **Usage**: Select objects, set island margin, and click `Smart UV Unwrap`.

3. **Shade Smooth & Auto Smooth**: Smooths the shading on selected or all objects.
    - **Auto Smooth**: Option to enable/disable auto smooth.
    - **Auto Smooth Angle**: Set the auto smooth angle (default: `30°`).
    - **Usage**: Select objects, set options, and click `Shade Smooth`.

4. **Remove Doubles**: Merges vertices within a specified distance on selected or all objects.
    - **Usage**: Select objects and click `Remove Doubles`.

### EasyOps Panel
1. **Bevel**: Adds a bevel modifier to selected or all objects.
    - **Width**: Default width set to `0.02`.
    - **Segments**: Default number of segments set to `3`.
    - **Profile**: Default profile set to `0.7`.
    - **Usage**: Select objects and click `Bevel`.

2. **Boolean Operations**:
    - **Boolean Difference**: Subtracts the active object from the selected objects and turns the active object into wireframe.
    - **Boolean Union**: Unites the active object and selected objects, turns the active object into wireframe.
    - **Boolean Intersect**: Keeps the intersection of the active object and selected objects, turns the active object into wireframe.
    - **EASYOPS_CUTS Collection**: All boolean effectors (wireframe objects) are automatically moved to this collection.
    - **Usage**: Select target objects, choose the active object, and click the appropriate boolean operation.

3. **Smart Decimate**: Adds a decimate modifier to selected or all objects.
    - **Usage**: Select objects and click `Smart Decimate`.

4. **Flat Shading**: Sets the shading of selected or all objects to flat shading.
    - **Usage**: Select objects and click `Flat Shading`.

5. **Clean Geometry**: Cleans up geometry by merging vertices by distance, deleting loose geometry, and dissolving degenerate geometry.
    - **Usage**: Select objects and click `Clean Geometry`.

6. **Smart Apply**: Applies all boolean modifiers on the selected objects while preserving other modifiers.
    - **Usage**: Select objects and click `Smart Apply`.

## Detailed Documentation

### Auto Rename
- **Description**: Automatically renames mesh objects and their mesh data with a custom prefix.
- **How to Use**: Select objects, set the desired prefix in the text field, and click `Auto Rename`.

### Smart UV Unwrap
- **Description**: Performs a Smart UV Unwrap with customizable island margin.
- **How to Use**: Select objects, adjust the island margin, and click `Smart UV Unwrap`.

### Shade Smooth & Auto Smooth
- **Description**: Smooth shading is applied to the selected mesh objects, with optional auto-smooth enabled at a custom angle.
- **How to Use**: Select objects, adjust options for auto-smooth and angle, and click `Shade Smooth`.

### Boolean Operations
- **Boolean Difference**: Subtracts the active object from the selected objects.
- **Boolean Union**: Unites the selected objects and the active object.
- **Boolean Intersect**: Keeps only the intersection of the selected objects and the active object.
- **Wireframe Mode**: The active object (boolean effector) will be displayed in wireframe mode after the operation.
- **Automatic Collection**: The active object will be moved to the `EASYOPS_CUTS` collection automatically after the operation.
  
### Clean Geometry
- **Description**: Cleans up mesh geometry by merging vertices by distance, deleting loose geometry, and dissolving degenerate faces/edges.
- **How to Use**: Select objects and click `Clean Geometry` to remove unnecessary geometry.

### Smart Apply
- **Description**: Applies all boolean modifiers while keeping other modifiers intact.
- **How to Use**: Select objects and click `Smart Apply` to finalize boolean operations while preserving other modifiers.

## License
This add-on is released under the MIT License.

## EasyScripts Addon

### Overview:
The **EasyScripts** add-on provides an easy way to manage and execute scripts within Blender. It includes two panels:
- A panel in the **Text Editor** for writing and saving new scripts.
- A panel in the **3D Viewport** for uploading, listing, running, editing, and removing scripts.

### Features:
1. **Text Editor Panel:**
   - Write scripts and save them directly to a persistent list.
   - Provides a custom name for each script.

2. **3D Viewport Panel:**
   - Upload external scripts and save them to the persistent list.
   - Select a script from a dropdown to run, edit, or remove the script.
   - Scripts are stored persistently in a custom directory (`easy_scripts` folder).

### Installation:
1. Download the `EasyScripts` add-on as a `.py` file.
2. In Blender, go to **Edit > Preferences > Add-ons**.
3. Click **Install**, and select the `EasyScripts.py` file.
4. Enable the add-on in the list.
5. You will now see the **EasyScripts** tab in both the **Text Editor** and **3D Viewport**.

### Usage:
1. **Text Editor**:
   - Write your script in a text block.
   - Save the script via the **EasyScripts** panel in the **Text Editor**.
   
2. **3D Viewport**:
   - Upload, run, edit, or remove previously saved scripts via the **EasyScripts** panel in the **3D Viewport**.


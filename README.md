
# EasyUtils & EasyOps for Blender 2.93/4.xx

**EasyUtils & EasyOps** is a Blender add-on that provides a set of tools designed to make common mesh operations easier and faster. This includes auto-renaming, UV unwrapping, smart apply operations, booleans with automatic wireframe mode, geometry cleaning, and more. All boolean effectors are automatically moved to a dedicated collection called `EASYOPS_CUTS`. For any extra information please refer [here](https://asian-mario.github.io/easyops-doc/)

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
The add-on creates a new tab in the **3D Viewport** called **Easy Utils**. Please refer [here](https://asian-mario.github.io/easyops-doc/) for documentation.

## License
This add-on is released under the MIT License.



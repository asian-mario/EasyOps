import bpy
from bpy.props import (
    StringProperty,
    FloatProperty,
    BoolProperty,
    EnumProperty,
    PointerProperty,
)


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
    sharpen_angle: FloatProperty(
        name="Sharpen Angle",
        description="Angle threshold for edge shaprening",
        default=30.0,
        min=1.0,
        max=180.0,
        subtype='ANGLE'
    )
    """
    Deprecated:
    
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
    """
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
    freeform_extrude_depth: FloatProperty(
        name="FreeForm Extrude Depth",
        description="Default depth for FreeForm boolean extrusion",
        default=1.0,
        min=0.01,
        max=10.0
    )
    freeform_both_directions: BoolProperty(
        name="FreeForm Both Directions",
        description="Extrude FreeForm boolean in both directions",
        default=True
    )
    surface_drawing_mode: BoolProperty(
        name="Surface Drawing",
        description="Draw booleans on object surface using normals",
        default=False
    )
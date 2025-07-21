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
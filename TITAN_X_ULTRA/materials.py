"""Materials for TITAN X ULTRA (Blender 2.82.7 compatible).

The module intentionally uses only the stable Principled BSDF inputs that were
available in Blender 2.82.  Dimensions and scene scale are managed by main.py;
materials are independent from the robot geometry.
"""

import bpy


def _set_input(node, names, value):
    """Set the first input that exists (also keeps the file usable in Blender 4)."""
    for name in names:
        socket = node.inputs.get(name)
        if socket is not None:
            socket.default_value = value
            return True
    return False


def _principled_material(name, color, metallic, roughness, emission=None):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name=name)

    material.use_nodes = True
    material.diffuse_color = color
    material.metallic = metallic
    material.roughness = roughness

    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled is None:
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        material.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    _set_input(principled, ("Base Color",), color)
    _set_input(principled, ("Metallic",), metallic)
    _set_input(principled, ("Roughness",), roughness)
    _set_input(principled, ("Specular", "Specular IOR Level"), 0.45)

    if emission is not None:
        emission_color, emission_strength = emission
        _set_input(principled, ("Emission", "Emission Color"), emission_color)
        # Emission Strength did not exist on the 2.82 Principled node.  When it
        # does exist (newer Blender), keep it restrained.
        _set_input(principled, ("Emission Strength",), emission_strength)

    material["titan_x_role"] = name
    return material


def create_materials():
    """Create or update the shared palette and return it by semantic key."""
    palette = {
        "gunmetal": _principled_material(
            "TXU_Gunmetal", (0.075, 0.09, 0.105, 1.0), 0.82, 0.28
        ),
        "matte_black": _principled_material(
            "TXU_MatteBlack", (0.012, 0.016, 0.021, 1.0), 0.10, 0.58
        ),
        "brushed_steel": _principled_material(
            "TXU_BrushedSteel", (0.32, 0.36, 0.39, 1.0), 0.92, 0.22
        ),
        "red_indicator": _principled_material(
            "TXU_RedIndicator",
            (0.34, 0.008, 0.012, 1.0),
            0.18,
            0.30,
            emission=((0.65, 0.005, 0.008, 1.0), 1.2),
        ),
        "rubber": _principled_material(
            "TXU_Rubber", (0.008, 0.010, 0.012, 1.0), 0.0, 0.78
        ),
        "dark_panel": _principled_material(
            "TXU_DarkPanel", (0.025, 0.035, 0.045, 1.0), 0.56, 0.38
        ),
        "safety_red": _principled_material(
            "TXU_SafetyRed", (0.42, 0.018, 0.015, 1.0), 0.35, 0.34
        ),
    }
    return palette


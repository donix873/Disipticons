"""Editable chassis module for TITAN X ULTRA.

The module targets the Blender 2.82 Python API.  One Blender unit represents
one millimetre; ``main.py`` is expected to set ``scale_length`` to 0.001.
The geometry is a visual engineering concept, not a fabrication drawing.
"""

import math

import bpy


COLLECTION_NAME = "TXU_CHASSIS"


def _collection(name, parent=None):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        if parent is None:
            bpy.context.scene.collection.children.link(collection)
        else:
            parent.children.link(collection)
    return collection


def _move_to_collection(obj, target):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def _fallback_material(name, color, metallic=0.0, roughness=0.5):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material.diffuse_color = color
        material.use_nodes = True
        principled = material.node_tree.nodes.get("Principled BSDF")
        if principled is not None:
            principled.inputs["Base Color"].default_value = color
            principled.inputs["Metallic"].default_value = metallic
            principled.inputs["Roughness"].default_value = roughness
    return material


def _material(materials, key):
    if materials and materials.get(key) is not None:
        return materials[key]
    defaults = {
        "gunmetal": ("TXU fallback gunmetal", (0.08, 0.10, 0.13, 1.0), 0.72, 0.30),
        "matte_black": ("TXU fallback matte black", (0.018, 0.022, 0.028, 1.0), 0.12, 0.66),
        "brushed_steel": ("TXU fallback steel", (0.30, 0.34, 0.38, 1.0), 0.86, 0.25),
        "red_indicator": ("TXU fallback red", (0.55, 0.012, 0.018, 1.0), 0.20, 0.28),
        "rubber": ("TXU fallback rubber", (0.008, 0.010, 0.013, 1.0), 0.0, 0.82),
        "dark_panel": ("TXU fallback dark panel", (0.04, 0.05, 0.065, 1.0), 0.45, 0.42),
    }
    values = defaults[key]
    return _fallback_material(values[0], values[1], values[2], values[3])


def _tag(obj, category, exportable=True):
    obj["titan_x_ultra_part"] = True
    obj["category"] = category
    obj["exportable"] = exportable
    return obj


def _box(name, dimensions, location, material, target, bevel=1.5):
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Edge softening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    _move_to_collection(obj, target)
    return obj


def _cylinder(name, radius, depth, location, rotation, material, target, vertices=32, bevel=0.8):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Edge softening", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    _move_to_collection(obj, target)
    return obj


def _panel_mesh(name, vertices, faces, material, target, bevel=1.2):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Safe panel edges", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
    return obj


def _side_guard(name, side, material, target):
    """Create a low sloped side guard; ``side`` is -1 or +1."""
    y_inner = side * 94.0
    y_outer = side * 105.0
    vertices = [
        (-108.0, y_inner, 23.0),
        (100.0, y_inner, 23.0),
        (112.0, y_inner, 48.0),
        (-98.0, y_inner, 63.0),
        (-108.0, y_outer, 23.0),
        (100.0, y_outer, 23.0),
        (112.0, y_outer, 48.0),
        (-98.0, y_outer, 63.0),
    ]
    faces = [
        (0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1),
        (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0),
    ]
    return _panel_mesh(name, vertices, faces, material, target, 1.4)


def build_chassis(materials=None):
    """Build and return the editable chassis assembly.

    ``materials`` is a dictionary produced by ``materials.create_materials``.
    The returned mapping contains the root empty, collections and named lists.
    Overall chassis bounds are approximately 256 x 244 x 82 mm, leaving room
    inside the 300 mm competition envelope for the lift mechanism.
    """
    gunmetal = _material(materials, "gunmetal")
    matte_black = _material(materials, "matte_black")
    steel = _material(materials, "brushed_steel")
    red = _material(materials, "red_indicator")
    rubber = _material(materials, "rubber")
    dark_panel = _material(materials, "dark_panel")

    root_collection = _collection(COLLECTION_NAME)
    frame_collection = _collection("TXU_FRAME", root_collection)
    wheel_collection = _collection("TXU_WHEELS", root_collection)
    armor_collection = _collection("TXU_ARMOR", root_collection)
    mounting_collection = _collection("TXU_MOUNTS", root_collection)
    electronics_collection = _collection("TXU_ELECTRONICS_MOCKUP", root_collection)

    root = bpy.data.objects.new("TITAN_X_ULTRA_CHASSIS_ROOT", None)
    root_collection.objects.link(root)
    root["assembly"] = "chassis"
    root["units"] = "millimetres"
    root["design_note"] = "Digital concept; dimensions require physical validation."

    frame = []
    armor = []
    top_covers = []
    wheels = []
    mounts = []
    electronics = []

    frame.append(_tag(_box("TXU chassis floor", (228.0, 188.0, 12.0), (0.0, 0.0, 31.0), gunmetal, frame_collection, 3.5), "frame"))
    frame.append(_tag(_box("TXU front crossmember", (22.0, 174.0, 18.0), (102.0, 0.0, 43.0), steel, frame_collection, 2.0), "frame"))
    frame.append(_tag(_box("TXU rear crossmember", (20.0, 174.0, 18.0), (-103.0, 0.0, 43.0), steel, frame_collection, 2.0), "frame"))
    frame.append(_tag(_box("TXU left longitudinal rail", (184.0, 16.0, 22.0), (-2.0, 78.0, 45.0), dark_panel, frame_collection, 2.0), "frame"))
    frame.append(_tag(_box("TXU right longitudinal rail", (184.0, 16.0, 22.0), (-2.0, -78.0, 45.0), dark_panel, frame_collection, 2.0), "frame"))

    armor.append(_tag(_side_guard("TXU left side guard", 1, gunmetal, armor_collection), "protective_panel"))
    armor.append(_tag(_side_guard("TXU right side guard", -1, gunmetal, armor_collection), "protective_panel"))
    armor.append(_tag(_box("TXU rear protective bumper", (18.0, 196.0, 30.0), (-119.0, 0.0, 41.0), dark_panel, armor_collection, 3.5), "protective_panel"))
    armor.append(_tag(_box("TXU front lower guard", (16.0, 190.0, 14.0), (98.0, 0.0, 25.0), gunmetal, armor_collection, 2.2), "protective_panel"))
    armor.append(_tag(_box("TXU left service panel", (92.0, 5.0, 31.0), (-34.0, 88.5, 66.0), dark_panel, armor_collection, 1.5), "removable_panel"))
    armor.append(_tag(_box("TXU right service panel", (92.0, 5.0, 31.0), (-34.0, -88.5, 66.0), dark_panel, armor_collection, 1.5), "removable_panel"))

    # Three opaque, independently removable cover panels hide the internal
    # mock-ups.  The 20 mm gaps centred at y = +/-43 mm are intentional
    # longitudinal lift-arm channels, not transparent windows.
    top_covers.append(_tag(_box(
        "TXU removable center top cover", (210.0, 64.0, 8.0),
        (-10.0, 0.0, 83.0), gunmetal, armor_collection, 2.0,
    ), "removable_top_cover"))
    top_covers.append(_tag(_box(
        "TXU removable left top cover", (210.0, 32.0, 8.0),
        (-10.0, 70.0, 83.0), dark_panel, armor_collection, 2.0,
    ), "removable_top_cover"))
    top_covers.append(_tag(_box(
        "TXU removable right top cover", (210.0, 32.0, 8.0),
        (-10.0, -70.0, 83.0), dark_panel, armor_collection, 2.0,
    ), "removable_top_cover"))
    armor.extend(top_covers)

    wheel_centers = [
        (70.0, 111.0, 40.0), (70.0, -111.0, 40.0),
        (-70.0, 111.0, 40.0), (-70.0, -111.0, 40.0),
    ]
    for index, center in enumerate(wheel_centers, 1):
        wheel = _tag(_cylinder(
            "TXU wheel %02d" % index, 32.0, 22.0, center,
            (math.pi / 2.0, 0.0, 0.0), rubber, wheel_collection, 36, 1.1,
        ), "wheel")
        hub = _tag(_cylinder(
            "TXU hub %02d" % index, 11.5, 23.0, center,
            (math.pi / 2.0, 0.0, 0.0), steel, wheel_collection, 28, 0.6,
        ), "wheel_hub")
        axle_center = (center[0], center[1] * 0.82, center[2])
        axle = _tag(_cylinder(
            "TXU axle %02d" % index, 6.0, 32.0, axle_center,
            (math.pi / 2.0, 0.0, 0.0), steel, mounting_collection, 24, 0.4,
        ), "axle")
        wheels.extend([wheel, hub])
        mounts.append(axle)

    for index, y_value in enumerate((-43.0, 43.0), 1):
        mount = _tag(_box(
            "TXU lift bearing mount %02d" % index,
            (18.0, 16.0, 35.0), (42.0, y_value, 70.0), steel,
            mounting_collection, 2.0,
        ), "mechanism_mount")
        mounts.append(mount)

    for side_index, y_value in enumerate((-72.0, 72.0), 1):
        for x_index, x_value in enumerate((-84.0, 0.0, 84.0), 1):
            fastener = _tag(_cylinder(
                "TXU deck fastener %d%d" % (side_index, x_index),
                3.0, 3.0, (x_value, y_value, 38.5), (0.0, 0.0, 0.0),
                matte_black, mounting_collection, 20, 0.25,
            ), "fastener")
            mounts.append(fastener)

    electronics.append(_tag(_box(
        "TXU sealed battery enclosure", (82.0, 70.0, 32.0),
        (-47.0, 0.0, 56.0), dark_panel, electronics_collection, 3.0,
    ), "electronics_mockup", False))
    electronics.append(_tag(_box(
        "TXU sealed controller enclosure", (62.0, 58.0, 24.0),
        (39.0, 0.0, 52.0), matte_black, electronics_collection, 2.5,
    ), "electronics_mockup", False))
    electronics.append(_tag(_box(
        "TXU power isolation module", (30.0, 25.0, 20.0),
        (-99.0, 70.0, 64.0), red, electronics_collection, 2.0,
    ), "electronics_mockup", False))

    all_parts = frame + armor + wheels + mounts + electronics
    for part in all_parts:
        part.parent = root

    return {
        "root": root,
        "collection": root_collection,
        "frame": frame,
        "armor": armor,
        "top_covers": top_covers,
        "wheels": wheels,
        "mounts": mounts,
        "electronics": electronics,
        "all_parts": all_parts,
        "wheel_centers": tuple(wheel_centers),
        "nominal_bounds_mm": ((-128.0, -122.5, 8.0), (128.0, 122.5, 87.5)),
        "mechanism_interface": {
            "recommended_pivot": (42.0, 0.0, 70.0),
            "arm_channels_y": (-43.0, 43.0),
            "arm_channel_width": 20.0,
            "front_clear_zone_x": (100.0, 145.0),
            "deck_height": 37.0,
        },
    }


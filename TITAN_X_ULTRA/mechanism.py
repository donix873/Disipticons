"""Safe animated lifting mechanism for TITAN X ULTRA.

The module uses millimetres as Blender units and is intentionally compatible
with Blender 2.82.7.  It is a visual kinematic demonstrator, not a validated
fabrication design or proof of physical lifting performance.
"""

import math

import bpy


COLLECTION_NAME = "TXU_MECHANISM"
PIVOT = (42.0, 0.0, 70.0)
REST_ANGLE_DEG = 0.0
LIFT_ANGLE_DEG = -35.0


def _collection(name):
    result = bpy.data.collections.get(name)
    if result is None:
        result = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(result)
    return result


def _move_to_collection(obj, target):
    for owner in list(obj.users_collection):
        owner.objects.unlink(obj)
    target.objects.link(obj)


def _fallback_material(name, color, metallic=0.0, roughness=0.45):
    material = bpy.data.materials.get(name)
    if material is not None:
        return material
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader is not None:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Roughness"].default_value = roughness
    return material


def _material(materials, key, fallback_name, color, metallic=0.0, roughness=0.45):
    if materials and materials.get(key) is not None:
        return materials[key]
    return _fallback_material(fallback_name, color, metallic, roughness)


def _mark(obj, role, moving=False):
    obj["titan_x_ultra_part"] = True
    obj["module"] = "mechanism"
    obj["role"] = role
    obj["moving_part"] = bool(moving)
    return obj


def _bevelled_box(name, dimensions, location, material, target, bevel=1.5):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0.0:
        modifier = obj.modifiers.new("Safe edge radius", "BEVEL")
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.append(material)
    _move_to_collection(obj, target)
    return obj


def _cylinder(name, radius, depth, location, rotation, material, target, vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=radius,
        depth=depth,
        location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    _move_to_collection(obj, target)
    return obj


def _wedge(name, x_rear, x_front, y_center, width, z_floor, z_rear, material, target):
    """Create a closed, blunt protective wedge with rounded edges."""
    y0 = y_center - width * 0.5
    y1 = y_center + width * 0.5
    z_nose = z_floor + 5.0
    vertices = [
        (x_rear, y0, z_floor),
        (x_front, y0, z_floor),
        (x_front, y0, z_nose),
        (x_rear, y0, z_rear),
        (x_rear, y1, z_floor),
        (x_front, y1, z_floor),
        (x_front, y1, z_nose),
        (x_rear, y1, z_rear),
    ]
    faces = [
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (3, 2, 6, 7),
        (0, 3, 7, 4),
    ]
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    target.objects.link(obj)
    obj.data.materials.append(material)
    modifier = obj.modifiers.new("Blunt edge radius", "BEVEL")
    modifier.width = 1.2
    modifier.segments = 2
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    return obj


def _parent_at_pivot(child, pivot):
    world = child.matrix_world.copy()
    child.parent = pivot
    child.matrix_world = world


def build_mechanism(materials=None):
    """Build the lift and return named objects for integration and animation."""
    target = _collection(COLLECTION_NAME)
    steel = _material(
        materials, "brushed_steel", "TXU fallback steel",
        (0.28, 0.32, 0.36, 1.0), 0.82, 0.28,
    )
    gunmetal = _material(
        materials, "gunmetal", "TXU fallback gunmetal",
        (0.075, 0.09, 0.11, 1.0), 0.72, 0.32,
    )
    dark = _material(
        materials, "matte_black", "TXU fallback matte black",
        (0.018, 0.022, 0.027, 1.0), 0.12, 0.68,
    )
    red = _material(
        materials, "red_indicator", "TXU fallback red marker",
        (0.55, 0.015, 0.02, 1.0), 0.18, 0.35,
    )

    pivot = bpy.data.objects.new("TXU_lift_pivot", None)
    pivot.location = PIVOT
    pivot.empty_display_type = "PLAIN_AXES"
    pivot.empty_display_size = 14.0
    target.objects.link(pivot)
    pivot["motion"] = "safe_demonstration_only"
    pivot["rotation_axis"] = "Y"
    pivot["minimum_angle_degrees"] = LIFT_ANGLE_DEG
    pivot["maximum_angle_degrees"] = REST_ANGLE_DEG

    moving = []
    arms = []
    forks = []
    for side, y in (("L", 43.0), ("R", -43.0)):
        arm = _mark(
            _bevelled_box(
                "TXU_lift_arm_" + side,
                (104.0, 12.0, 13.0),
                (PIVOT[0] + 48.0, y, PIVOT[2]),
                gunmetal,
                target,
                2.4,
            ),
            "lift_arm",
            True,
        )
        _parent_at_pivot(arm, pivot)
        arms.append(arm)
        moving.append(arm)

        # A broad, rounded fork sits above the floor at rest.  It is a lifting
        # surface, not a sharpened or impact-producing element.
        fork = _mark(
            _wedge(
                "TXU_lift_fork_" + side,
                123.0,
                147.0,
                y,
                22.0,
                18.0,
                53.0,
                steel,
                target,
            ),
            "lift_fork",
            True,
        )
        _parent_at_pivot(fork, pivot)
        forks.append(fork)
        moving.append(fork)

        connector = _mark(
            _bevelled_box(
                "TXU_fork_connector_" + side,
                (18.0, 14.0, 28.0),
                (PIVOT[0] + 82.0, y, 58.0),
                steel,
                target,
                2.0,
            ),
            "fork_connector",
            True,
        )
        _parent_at_pivot(connector, pivot)
        moving.append(connector)

        knuckle = _mark(
            _cylinder(
                "TXU_pivot_knuckle_" + side,
                14.0,
                16.0,
                (PIVOT[0], y, PIVOT[2]),
                (math.pi * 0.5, 0.0, 0.0),
                gunmetal,
                target,
                32,
            ),
            "moving_knuckle",
            True,
        )
        _parent_at_pivot(knuckle, pivot)
        moving.append(knuckle)

    crossbar = _mark(
        _bevelled_box(
            "TXU_lift_crossbar",
            (16.0, 98.0, 14.0),
            (PIVOT[0] + 82.0, 0.0, PIVOT[2]),
            steel,
            target,
            2.2,
        ),
        "moving_crossbar",
        True,
    )
    _parent_at_pivot(crossbar, pivot)
    moving.append(crossbar)

    fixed = []
    supports = []
    for side, y in (("L", 43.0), ("R", -43.0)):
        support = _mark(
            _bevelled_box(
                "TXU_pivot_support_" + side,
                (34.0, 12.0, 52.0),
                (PIVOT[0] - 4.0, y, 49.0),
                gunmetal,
                target,
                3.0,
            ),
            "fixed_pivot_support",
            False,
        )
        supports.append(support)
        fixed.append(support)

        stop = _mark(
            _bevelled_box(
                "TXU_travel_stop_" + side,
                (18.0, 18.0, 14.0),
                (PIVOT[0] - 24.0, y, 81.0),
                red,
                target,
                2.0,
            ),
            "mechanical_travel_stop",
            False,
        )
        stop["limit_degrees"] = abs(LIFT_ANGLE_DEG)
        fixed.append(stop)

    pin = _mark(
        _cylinder(
            "TXU_main_pivot_pin",
            8.0,
            106.0,
            PIVOT,
            (math.pi * 0.5, 0.0, 0.0),
            steel,
            target,
            40,
        ),
        "fixed_pivot_pin",
        False,
    )
    fixed.append(pin)

    # Three fixed, blunt nose panels guide an object onto the two forks while
    # leaving the moving parts visually readable.
    wedges = []
    for label, y, width in (("C", 0.0, 42.0), ("L", 72.0, 28.0), ("R", -72.0, 28.0)):
        wedge = _mark(
            _wedge(
                "TXU_protective_wedge_" + label,
                108.0,
                147.0,
                y,
                width,
                18.0,
                47.0,
                dark,
                target,
            ),
            "fixed_protective_wedge",
            False,
        )
        wedges.append(wedge)
        fixed.append(wedge)

    return {
        "pivot": pivot,
        "arms": arms,
        "forks": forks,
        "crossbar": crossbar,
        "supports": supports,
        "wedges": wedges,
        "moving": moving,
        "fixed": fixed,
        "all": moving + fixed,
    }


def animate_mechanism(parts, frame_start=1, frame_end=90):
    """Animate one controlled lift cycle without overshoot."""
    if not parts or parts.get("pivot") is None:
        raise ValueError("Mechanism parts must contain a 'pivot' object")
    if frame_end <= frame_start + 2:
        raise ValueError("Animation interval is too short")

    pivot = parts["pivot"]
    middle = int(round((frame_start + frame_end) * 0.5))
    for frame, angle in (
        (frame_start, REST_ANGLE_DEG),
        (middle, LIFT_ANGLE_DEG),
        (frame_end, REST_ANGLE_DEG),
    ):
        pivot.rotation_euler = (0.0, math.radians(angle), 0.0)
        pivot.keyframe_insert(data_path="rotation_euler", index=1, frame=frame)

    if pivot.animation_data and pivot.animation_data.action:
        for curve in pivot.animation_data.action.fcurves:
            for point in curve.keyframe_points:
                point.interpolation = "SINE"

    scene = bpy.context.scene
    scene.frame_start = min(scene.frame_start, frame_start)
    scene.frame_end = max(scene.frame_end, frame_end)
    scene.frame_set(frame_start)
    return {
        "frame_start": frame_start,
        "frame_lifted": middle,
        "frame_end": frame_end,
        "rest_angle_degrees": REST_ANGLE_DEG,
        "lift_angle_degrees": LIFT_ANGLE_DEG,
    }


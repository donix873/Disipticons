"""Lighting and comparable review cameras for TITAN X ULTRA.

All locations are expressed in millimetres because the project uses Blender
units as millimetres with ``scene.unit_settings.scale_length = 0.001``.
Only API available in Blender 2.82.7 is required.
"""

import math
import os

import bpy
from mathutils import Vector


CAMERA_SPECS = {
    "TXU_Camera_Hero": ((390.0, -455.0, 285.0), (0.0, 5.0, 48.0), 52.0),
    "TXU_Camera_Top": ((0.0, 10.0, 720.0), (0.0, 10.0, 25.0), 58.0),
    "TXU_Camera_Internal": ((245.0, -285.0, 205.0), (0.0, 18.0, 42.0), 60.0),
}


def _collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _link_only(obj, collection):
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    for current in list(obj.users_collection):
        if current != collection:
            current.objects.unlink(obj)


def _look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def _camera(name, location, target, lens, collection):
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "CAMERA":
        data = bpy.data.cameras.new(name + "_Data")
        obj = bpy.data.objects.new(name, data)
    _link_only(obj, collection)
    obj.location = location
    obj.data.lens = lens
    obj.data.sensor_width = 36.0
    obj.data.clip_start = 2.0
    obj.data.clip_end = 3000.0
    _look_at(obj, target)
    obj["review_view"] = True
    return obj


def create_cameras():
    """Create stable hero/top/internal review views and return a name dictionary."""
    collection = _collection("TXU_CAMERAS")
    cameras = {}
    for name, spec in CAMERA_SPECS.items():
        location, target, lens = spec
        cameras[name] = _camera(name, location, target, lens, collection)

    # A strict downward orthographic camera makes the dimensional review
    # repeatable.  Zero rotation points the camera's local -Z axis down and
    # keeps robot X horizontal in the 16:9 frame (no look-at roll ambiguity).
    top_camera = cameras["TXU_Camera_Top"]
    top_camera.rotation_euler = (0.0, 0.0, 0.0)
    top_camera.data.type = "ORTHO"
    # In Blender's 16:9 camera framing the vertical field is narrower than the
    # named orthographic scale.  560 mm gives about 315 mm vertically, keeping
    # the full 287 x 245 mm envelope inside frame with an inspection margin.
    top_camera.data.ortho_scale = 560.0

    bpy.context.scene.camera = cameras["TXU_Camera_Hero"]
    return cameras


def _area_light(name, location, target, energy, size, color, collection):
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "LIGHT":
        data = bpy.data.lights.new(name + "_Data", type="AREA")
        obj = bpy.data.objects.new(name, data)
    _link_only(obj, collection)
    obj.location = location
    obj.data.type = "AREA"
    obj.data.energy = energy
    obj.data.size = size
    obj.data.color = color
    _look_at(obj, target)
    return obj


def setup_lighting():
    """Create a restrained three-point studio rig without decorative neon."""
    collection = _collection("TXU_LIGHTS")
    target = (0.0, 10.0, 35.0)
    lights = {
        "key": _area_light(
            "TXU_Light_Key", (310.0, -340.0, 430.0), target,
            6500000.0, 260.0, (1.0, 0.90, 0.80), collection
        ),
        "fill": _area_light(
            "TXU_Light_Fill", (-350.0, -160.0, 250.0), target,
            2800000.0, 300.0, (0.64, 0.76, 1.0), collection
        ),
        "rim": _area_light(
            "TXU_Light_Rim", (185.0, 330.0, 330.0), target,
            4500000.0, 220.0, (0.78, 0.86, 1.0), collection
        ),
    }

    world = bpy.context.scene.world
    if world is None:
        world = bpy.data.worlds.new("TXU_World")
        bpy.context.scene.world = world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    if background is not None:
        background.inputs["Color"].default_value = (0.008, 0.012, 0.020, 1.0)
        background.inputs["Strength"].default_value = 0.42
    return lights


def setup_render(scene, output_dir=None):
    """Configure a lightweight Mac-friendly render and return scene assets."""
    # Blender 2.82 uses BLENDER_EEVEE; newer versions accept EEVEE_NEXT only.
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.fps = 30
    scene.render.fps_base = 1.0

    if hasattr(scene, "eevee"):
        eevee = scene.eevee
        if hasattr(eevee, "use_gtao"):
            eevee.use_gtao = True
        if hasattr(eevee, "gtao_distance"):
            eevee.gtao_distance = 3.0
        if hasattr(eevee, "gtao_factor"):
            eevee.gtao_factor = 1.15
        if hasattr(eevee, "use_soft_shadows"):
            eevee.use_soft_shadows = True
        if hasattr(eevee, "taa_render_samples"):
            eevee.taa_render_samples = 48

    scene.view_settings.view_transform = "Filmic"
    # A small global lift keeps the matte-black body readable while the
    # indicator material remains restrained by its low emission value.
    scene.view_settings.exposure = 0.60
    scene.view_settings.gamma = 1.0
    try:
        scene.view_settings.look = "Medium High Contrast"
    except TypeError:
        pass

    if output_dir:
        output_dir = os.path.abspath(output_dir)
        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)
        scene.render.filepath = os.path.join(output_dir, "titan_x_ultra_hero.png")

    cameras = create_cameras()
    lights = setup_lighting()
    return {"cameras": cameras, "lights": lights}


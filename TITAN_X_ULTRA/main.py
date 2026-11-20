"""Assemble the editable TITAN X ULTRA scene.

Run from this directory:
    blender --background --python main.py
Optional comparable stills:
    blender --background --python main.py -- --render-stills

The model is a digital kinematic concept, not proof of a working physical robot.
Geometry uses millimetres as Blender units and avoids APIs newer than 2.82.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent
OUTPUT_BLEND = ROOT / "TITAN_X_ULTRA.blend"
RENDER_DIR = ROOT / "renders"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import chassis
import materials
import mechanism
import render_setup


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-stills", action="store_true")
    argv = []
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    return parser.parse_args(argv)


def clean_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for collection in list(bpy.data.collections):
        bpy.data.collections.remove(collection)
    for action in list(bpy.data.actions):
        if action.users == 0:
            bpy.data.actions.remove(action)


def configure_scene(scene):
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 0.001
    scene.frame_start = 1
    scene.frame_end = 90
    scene.render.fps = 30
    scene["project"] = "TITAN X ULTRA"
    scene["model_status"] = "digital kinematic concept"
    scene["physical_validation"] = False
    scene["target_api"] = "Blender 2.82.7"


def add_presentation_floor(material_map):
    collection = bpy.data.collections.new("TXU_PRESENTATION")
    bpy.context.scene.collection.children.link(collection)
    bpy.ops.mesh.primitive_plane_add(size=1200.0, location=(0.0, 0.0, 7.0))
    floor = bpy.context.object
    floor.name = "TXU presentation floor (not robot)"
    floor.data.materials.append(material_map["matte_black"])
    floor["exclude_from_robot_bounds"] = True
    for owner in list(floor.users_collection):
        owner.objects.unlink(floor)
    collection.objects.link(floor)
    return floor


def robot_meshes():
    return [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and bool(obj.get("titan_x_ultra_part"))
    ]


def world_bounds(objects):
    points = []
    for obj in objects:
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    if not points:
        raise RuntimeError("No tagged robot mesh objects were created")
    minimum = tuple(min(point[index] for point in points) for index in range(3))
    maximum = tuple(max(point[index] for point in points) for index in range(3))
    dimensions = tuple(maximum[index] - minimum[index] for index in range(3))
    return minimum, maximum, dimensions


def measure_animation(scene, frames):
    report = {}
    maximum_dimensions = [0.0, 0.0, 0.0]
    tagged = robot_meshes()
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        minimum, maximum, dimensions = world_bounds(tagged)
        report[str(frame)] = {
            "min_mm": [round(value, 3) for value in minimum],
            "max_mm": [round(value, 3) for value in maximum],
            "dimensions_mm": [round(value, 3) for value in dimensions],
        }
        for axis in range(3):
            maximum_dimensions[axis] = max(maximum_dimensions[axis], dimensions[axis])
        if any(value > 300.0 + 1e-4 for value in dimensions):
            raise RuntimeError(
                "Robot exceeds the 300 mm envelope at frame %d: %s" %
                (frame, tuple(round(value, 3) for value in dimensions))
            )
    scene.frame_set(scene.frame_start)
    return report, maximum_dimensions


def scene_statistics(scene):
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    return {
        "blender_version_used": ".".join(str(value) for value in bpy.app.version),
        "target_blender_version": "2.82.7",
        "objects": len(scene.objects),
        "mesh_objects": len(meshes),
        "robot_mesh_objects": len(robot_meshes()),
        "vertices": sum(len(obj.data.vertices) for obj in meshes),
        "polygons": sum(len(obj.data.polygons) for obj in meshes),
        "materials": len(bpy.data.materials),
        "cameras": len([obj for obj in scene.objects if obj.type == "CAMERA"]),
        "lights": len([obj for obj in scene.objects if obj.type == "LIGHT"]),
        "unapplied_modifiers": sum(len(obj.modifiers) for obj in meshes),
    }


def render_stills(scene, chassis_parts, cameras):
    RENDER_DIR.mkdir(exist_ok=True)
    views = (
        ("hero", cameras["TXU_Camera_Hero"], False, 1),
        ("top", cameras["TXU_Camera_Top"], False, 1),
        ("internal", cameras["TXU_Camera_Internal"], True, 1),
        ("lifted", cameras["TXU_Camera_Hero"], False, 45),
    )
    covers = chassis_parts.get("top_covers", [])
    for name, camera, reveal_internal, frame in views:
        scene.camera = camera
        scene.frame_set(frame)
        for cover in covers:
            cover.hide_render = reveal_internal
        scene.render.filepath = str(RENDER_DIR / (name + ".png"))
        bpy.ops.render.render(write_still=True)
    for cover in covers:
        cover.hide_render = False
    scene.frame_set(1)


def main():
    args = parse_args()
    clean_scene()
    scene = bpy.context.scene
    configure_scene(scene)

    material_map = materials.create_materials()
    chassis_parts = chassis.build_chassis(material_map)
    mechanism_parts = mechanism.build_mechanism(material_map)
    animation = mechanism.animate_mechanism(mechanism_parts, 1, 90)
    presentation = render_setup.setup_render(scene, str(RENDER_DIR))
    add_presentation_floor(material_map)

    critical_frames = sorted(set((1, animation["frame_lifted"], 90)))
    bounds_by_frame, maximum_dimensions = measure_animation(scene, critical_frames)
    statistics = scene_statistics(scene)
    statistics["critical_frame_bounds"] = bounds_by_frame
    statistics["maximum_dimensions_mm"] = [round(value, 3) for value in maximum_dimensions]
    statistics["compatibility_note"] = (
        "Executed in the listed version; Blender 2.82.7 requires a separate target-machine run."
    )

    if args.render_stills:
        render_stills(scene, chassis_parts, presentation["cameras"])

    scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_BLEND))
    statistics["blend_size_bytes"] = os.path.getsize(str(OUTPUT_BLEND))
    (ROOT / "build_report.json").write_text(
        json.dumps(statistics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("TITAN_X_ULTRA_BUILD_OK")
    print(json.dumps(statistics, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

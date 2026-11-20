"""Runtime geometry checks for the assembled TITAN X ULTRA scene."""

import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parent


def tagged_meshes():
    return [
        obj for obj in bpy.context.scene.objects
        if obj.type == "MESH" and bool(obj.get("titan_x_ultra_part"))
    ]


def bounds(objects):
    points = []
    for obj in objects:
        points.extend(obj.matrix_world @ Vector(corner) for corner in obj.bound_box)
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return [maximum[axis] - minimum[axis] for axis in range(3)], minimum, maximum


def world_bvh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    vertices = [evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
    polygons = [tuple(vertex for vertex in polygon.vertices) for polygon in mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=False)
    evaluated.to_mesh_clear()
    return tree


def intended_joint_contact(moving_name, fixed_name):
    joint_tokens = (
        "pivot_support", "main_pivot_pin", "lift bearing mount",
    )
    if any(token in fixed_name for token in joint_tokens):
        return any(token in moving_name for token in ("lift_arm", "pivot_knuckle"))
    return False


def unexpected_overlaps(frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    meshes = tagged_meshes()
    moving = [obj for obj in meshes if bool(obj.get("moving_part"))]
    fixed = [obj for obj in meshes if not bool(obj.get("moving_part"))]
    fixed_trees = {obj.name: world_bvh(obj, depsgraph) for obj in fixed}
    overlaps = []
    for moving_obj in moving:
        moving_tree = world_bvh(moving_obj, depsgraph)
        for fixed_obj in fixed:
            if intended_joint_contact(moving_obj.name, fixed_obj.name):
                continue
            if moving_tree.overlap(fixed_trees[fixed_obj.name]):
                overlaps.append([moving_obj.name, fixed_obj.name])
    return overlaps


def main():
    scene = bpy.context.scene
    meshes = tagged_meshes()
    frames = list(range(scene.frame_start, scene.frame_end + 1, 5))
    if scene.frame_end not in frames:
        frames.append(scene.frame_end)
    measurements = {}
    maximum_dimensions = [0.0, 0.0, 0.0]
    moving_min_z = None
    collisions = {}
    for frame in frames:
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        dimensions, minimum, maximum = bounds(meshes)
        measurements[str(frame)] = [round(value, 3) for value in dimensions]
        maximum_dimensions = [
            max(maximum_dimensions[axis], dimensions[axis]) for axis in range(3)
        ]
        moving_objects = [obj for obj in meshes if bool(obj.get("moving_part"))]
        _, moving_minimum, _ = bounds(moving_objects)
        moving_min_z = moving_minimum[2] if moving_min_z is None else min(moving_min_z, moving_minimum[2])
        overlaps = unexpected_overlaps(frame)
        if overlaps:
            collisions[str(frame)] = overlaps

    covers = [obj for obj in meshes if obj.get("category") == "removable_top_cover"]
    opaque_covers = all(
        material.diffuse_color[3] >= 0.999
        for obj in covers for material in obj.data.materials
    )
    wheels = [obj for obj in meshes if obj.get("category") == "wheel"]
    report = {
        "sampled_frames": frames,
        "dimensions_by_frame_mm": measurements,
        "maximum_dimensions_mm": [round(value, 3) for value in maximum_dimensions],
        "envelope_pass": all(value <= 300.0 + 1e-4 for value in maximum_dimensions),
        "moving_minimum_z_mm": round(moving_min_z, 3),
        "above_floor_pass": moving_min_z >= 7.0,
        "top_cover_count": len(covers),
        "covers_opaque_pass": opaque_covers,
        "wheel_count": len(wheels),
        "four_wheels_pass": len(wheels) == 4,
        "unexpected_overlaps": collisions,
        "collision_sample_pass": not bool(collisions),
        "note": "BVH sampled every five frames; physical clearances still require prototype validation.",
    }
    scene.frame_set(scene.frame_start)
    (ROOT / "qa_runtime_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("TXU_QA_RUNTIME")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not report["envelope_pass"] or not report["above_floor_pass"]:
        raise RuntimeError("Critical geometry QA failed")


if __name__ == "__main__":
    main()

"""Re-import a compatibility export and print structural validation data."""

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def main():
    if "--" not in sys.argv:
        raise RuntimeError("Pass an FBX or GLB path after --")
    path = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if path.suffix.lower() == ".glb":
        bpy.ops.import_scene.gltf(filepath=str(path))
    elif path.suffix.lower() == ".fbx":
        bpy.ops.import_scene.fbx(filepath=str(path), automatic_bone_orientation=False)
    else:
        raise RuntimeError("Unsupported format: " + path.suffix)

    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    dimensions = [maximum[axis] - minimum[axis] for axis in range(3)]
    animated = [
        obj.name for obj in bpy.context.scene.objects
        if obj.animation_data is not None and obj.animation_data.action is not None
    ]
    report = {
        "file": path.name,
        "objects": len(bpy.context.scene.objects),
        "meshes": len(meshes),
        "materials": len(bpy.data.materials),
        "actions": len(bpy.data.actions),
        "animated_objects": animated,
        "dimensions_imported_units": [round(value, 6) for value in dimensions],
        "import_pass": len(meshes) == 54 and len(bpy.data.actions) >= 1,
    }
    output = path.with_name(path.stem + "_" + path.suffix.lower().lstrip(".") + "_validation.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("TXU_COMPAT_IMPORT_OK")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if not report["import_pass"]:
        raise RuntimeError("Compatibility import validation failed")


if __name__ == "__main__":
    main()

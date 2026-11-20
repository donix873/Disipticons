"""Export interchange files for Blender 2.82 and other older releases.

Run with the assembled file loaded:
    blender TITAN_X_ULTRA.blend --background --python export_compat.py
"""

import json
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent


def select_robot():
    bpy.ops.object.select_all(action="DESELECT")
    selected = set()
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and bool(obj.get("titan_x_ultra_part")):
            selected.add(obj)
            parent = obj.parent
            while parent is not None:
                selected.add(parent)
                parent = parent.parent
    for obj in selected:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.select_set(True)
    meshes = [obj for obj in selected if obj.type == "MESH"]
    bpy.context.view_layer.objects.active = meshes[0]
    return selected


def add_gltf_metre_root(selected):
    """Scale the millimetre-coordinate assembly to glTF metres."""
    root = bpy.data.objects.new("TXU_GLTF_METRE_SCALE", None)
    bpy.context.scene.collection.objects.link(root)
    records = []
    top_level = [obj for obj in selected if obj.parent not in selected]
    for obj in top_level:
        records.append((obj, obj.parent, obj.matrix_world.copy()))
        obj.parent = root
        obj.matrix_world = records[-1][2]
    root.scale = (0.001, 0.001, 0.001)
    root.select_set(True)
    selected.add(root)
    return root, records


def remove_gltf_metre_root(selected, root, records):
    for obj, old_parent, old_matrix in records:
        obj.parent = old_parent
        obj.matrix_world = old_matrix
    selected.remove(root)
    bpy.data.objects.remove(root, do_unlink=True)
    bpy.context.view_layer.update()
    for obj in selected:
        obj.select_set(True)


def main():
    selected = select_robot()
    glb_path = ROOT / "TITAN_X_ULTRA_COMPAT_2_82.glb"
    fbx_path = ROOT / "TITAN_X_ULTRA_COMPAT_2_82.fbx"

    gltf_root, parent_records = add_gltf_metre_root(selected)
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_cameras=False,
        export_lights=False,
        export_animations=True,
        export_frame_range=True,
        export_force_sampling=True,
        export_nla_strips=False,
        export_materials="EXPORT",
        export_draco_mesh_compression_enable=False,
        export_apply=True,
        export_extras=False,
        export_yup=True,
    )
    remove_gltf_metre_root(selected, gltf_root, parent_records)

    bpy.ops.export_scene.fbx(
        filepath=str(fbx_path),
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        use_mesh_modifiers=True,
        use_triangles=True,
        use_custom_props=False,
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
        bake_anim=True,
        bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,
        path_mode="AUTO",
    )

    report = {
        "source_blend": "TITAN_X_ULTRA.blend",
        "selected_objects": len(selected),
        "mesh_objects": len([obj for obj in selected if obj.type == "MESH"]),
        "animation_frames": [bpy.context.scene.frame_start, bpy.context.scene.frame_end],
        "files": {
            glb_path.name: glb_path.stat().st_size,
            fbx_path.name: fbx_path.stat().st_size,
        },
        "import_note": "In Blender 2.82 use File > Import, not File > Open.",
    }
    (ROOT / "compat_export_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("TXU_COMPAT_EXPORT_OK")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

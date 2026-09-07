#!/usr/bin/env python3
"""
scripts/render_synthetic_set.py

Renders 32 multi-view frames (24 circular orbit + 8 top) from Poly Haven Camera_01
using Blender headless (bpy). Generates calibrated ground-truth camera matrices K, [R|t]
conforming to docs/p3/spatial_context_schema.json.
"""

import sys
import os
import json
import math
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BLEND_FILE = ROOT_DIR / "scratch" / "polyhaven_camera" / "Camera_01_1k.blend"
OUTPUT_DIR = ROOT_DIR / "assets" / "p3" / "synthetic_object"
IMG_DIR = OUTPUT_DIR / "images"
CAM_FILE = OUTPUT_DIR / "cameras.json"

# In Blender headless mode, this script runs via:
# blender -b <blend_file> -P scripts/render_synthetic_set.py

try:
    import bpy
    import mathutils
    import numpy as np
except ImportError:
    print("This script must be executed inside Blender's python environment.")
    sys.exit(1)


def setup_scene_and_camera():
    os.makedirs(IMG_DIR, exist_ok=True)

    # 1. Find bounding box center and dimensions of mesh objects
    mesh_objs = [o for o in bpy.data.objects if o.type == 'MESH']
    min_co = [float('inf')] * 3
    max_co = [float('-inf')] * 3

    for o in mesh_objs:
        for corner in o.bound_box:
            world_corner = o.matrix_world @ mathutils.Vector(corner)
            for i in range(3):
                min_co[i] = min(min_co[i], world_corner[i])
                max_co[i] = max(max_co[i], world_corner[i])

    center = mathutils.Vector([(min_co[i] + max_co[i]) / 2.0 for i in range(3)])
    dims = [round(max_co[i] - min_co[i], 4) for i in range(3)]
    print(f"BBox Min: {min_co}, Max: {max_co}")
    print(f"Object Center: {center}, Dimensions: {dims} meters")

    # 2. Setup Lighting (Studio 3-point light rig)
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

    # Key light
    key_light = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_light.energy = 3.5
    key_obj = bpy.data.objects.new(name="KeyLight", object_data=key_light)
    bpy.context.scene.collection.objects.link(key_obj)
    key_obj.rotation_euler = (math.radians(45), math.radians(15), math.radians(45))

    # Fill light
    fill_light = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_light.energy = 1.5
    fill_obj = bpy.data.objects.new(name="FillLight", object_data=fill_light)
    bpy.context.scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(30), math.radians(-30), math.radians(-135))

    # Top light
    top_light = bpy.data.lights.new(name="TopLight", type='SUN')
    top_light.energy = 1.0
    top_obj = bpy.data.objects.new(name="TopLight", object_data=top_light)
    bpy.context.scene.collection.objects.link(top_obj)
    top_obj.rotation_euler = (math.radians(0), math.radians(0), 0)

    # World background color
    if bpy.context.scene.world:
        bpy.context.scene.world.use_nodes = True
        bg_node = bpy.context.scene.world.node_tree.nodes.get("Background")
        if bg_node:
            bg_node.inputs[0].default_value = (0.08, 0.08, 0.09, 1.0) # clean dark neutral studio
            bg_node.inputs[1].default_value = 0.8

    # 3. Setup Camera
    for obj in list(bpy.data.objects):
        if obj.type == 'CAMERA':
            bpy.data.objects.remove(obj, do_unlink=True)

    cam_data = bpy.data.cameras.new(name="RenderCamera")
    cam_data.sensor_fit = 'HORIZONTAL'
    cam_data.sensor_width = 36.0 # 36mm full frame equivalent
    cam_data.lens = 50.0 # 50mm lens
    cam_obj = bpy.data.objects.new(name="RenderCamera", object_data=cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # 4. Render Settings
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'

    return cam_obj, center, dims


def render_all_views(cam_obj, center, dims):
    width = 1280
    height = 960
    sensor_w = cam_obj.data.sensor_width
    focal_mm = cam_obj.data.lens

    # Compute Intrinsics K
    # fx = f * (W / sensor_w)
    fx = focal_mm * (width / sensor_w)
    fy = fx # square pixels
    cx = width / 2.0
    cy = height / 2.0

    K_matrix = [
        [fx, 0.0, cx],
        [0.0, fy, cy],
        [0.0, 0.0, 1.0]
    ]

    # Coordinate transformation matrix S = diag(1, -1, -1)
    S = np.diag([1.0, -1.0, -1.0])

    distance = 0.58 # 58 cm from object center (perfect framing for 26 cm camera)
    total_frames = 32
    views = []

    # 24 circular orbit views (elevation 18 degrees)
    elev_orbit = math.radians(18.0)
    for i in range(24):
        azimuth = 2.0 * math.pi * (i / 24.0)
        views.append({
            "idx": i,
            "type": "orbit",
            "azimuth": azimuth,
            "elevation": elev_orbit,
        })

    # 8 top views (elevation 65 degrees, azimuth offset by 22.5 degrees)
    elev_top = math.radians(65.0)
    for j in range(8):
        azimuth = 2.0 * math.pi * (j / 8.0) + math.radians(22.5)
        views.append({
            "idx": 24 + j,
            "type": "top",
            "azimuth": azimuth,
            "elevation": elev_top,
        })

    frames_output = []

    for v in views:
        idx = v["idx"]
        az = v["azimuth"]
        el = v["elevation"]

        # Camera position
        x = center.x + distance * math.cos(el) * math.cos(az)
        y = center.y + distance * math.cos(el) * math.sin(az)
        z = center.z + distance * math.sin(el)
        pos = mathutils.Vector((x, y, z))

        cam_obj.location = pos

        # Track target (object center)
        direction = center - pos
        rot_quat = direction.to_track_quat('-Z', 'Y')
        cam_obj.rotation_euler = rot_quat.to_euler()

        # Update scene to ensure matrix_world is computed
        bpy.context.view_layer.update()

        # Extract world rotation and translation
        mat_world = cam_obj.matrix_world
        R_blender = np.array([
            [mat_world[0][0], mat_world[0][1], mat_world[0][2]],
            [mat_world[1][0], mat_world[1][1], mat_world[1][2]],
            [mat_world[2][0], mat_world[2][1], mat_world[2][2]],
        ], dtype=np.float64)
        C = np.array([mat_world[0][3], mat_world[1][3], mat_world[2][3]], dtype=np.float64)

        # OpenCV Extrinsics: R_cv = S * R_blender^T, t_cv = - R_cv * C
        R_cv = S @ R_blender.T
        t_cv = -R_cv @ C

        Rt_matrix = [
            [float(R_cv[0, 0]), float(R_cv[0, 1]), float(R_cv[0, 2]), float(t_cv[0])],
            [float(R_cv[1, 0]), float(R_cv[1, 1]), float(R_cv[1, 2]), float(t_cv[1])],
            [float(R_cv[2, 0]), float(R_cv[2, 1]), float(R_cv[2, 2]), float(t_cv[2])],
            [0.0, 0.0, 0.0, 1.0]
        ]

        frame_id = f"frame_{idx:04d}"
        img_filename = f"{frame_id}.png"
        img_rel_path = f"assets/p3/synthetic_object/images/{img_filename}"
        img_abs_path = str(IMG_DIR / img_filename)

        bpy.context.scene.render.filepath = img_abs_path
        bpy.ops.render.render(write_still=True)
        print(f"[{idx+1}/32] Rendered {img_filename} (type={v['type']}, az={math.degrees(az):.1f}°, el={math.degrees(el):.1f}°)")

        frame_data = {
            "frame_id": frame_id,
            "image_path": img_rel_path,
            "K": K_matrix,
            "Rt": Rt_matrix,
            "source": "capture",
            "timestamp": "2026-09-06T00:00:00Z",
            "metadata": {
                "view_type": v["type"],
                "azimuth_deg": round(math.degrees(az), 2),
                "elevation_deg": round(math.degrees(el), 2),
                "distance_m": distance,
                "object_center_m": [round(center.x, 4), round(center.y, 4), round(center.z, 4)],
                "object_dimensions_m": dims,
                "scale_unit": "meter"
            }
        }
        frames_output.append(frame_data)

    dataset_output = {
        "metadata": {
            "title": "Poly Haven Camera 01 Synthetic Multi-view Ground Truth Dataset",
            "object_name": "Vintage Camera 01",
            "object_dimensions_m": dims,
            "scale_unit": "meter",
            "width": width,
            "height": height,
            "focal_length_mm": focal_mm,
            "sensor_width_mm": sensor_w,
            "total_frames": len(frames_output),
            "views_orbit": 24,
            "views_top": 8,
            "license": "Creative Commons CC0 1.0 Universal",
            "schema_version": "1.0.0"
        },
        "frames": frames_output
    }

    with open(CAM_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset_output, f, indent=2)

    print(f"\nAll 32 frames rendered and cameras saved to: {CAM_FILE}")


def main():
    cam_obj, center, dims = setup_scene_and_camera()
    render_all_views(cam_obj, center, dims)


if __name__ == "__main__":
    main()

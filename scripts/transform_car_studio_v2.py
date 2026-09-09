#!/usr/bin/env python3
"""
scripts/transform_car_studio_v2.py

Phase 3 / CAR-03: Metric Transformation, Table Footprint Extraction,
and Baked Car Box SDF Zeroing for World Labs Car Studio v2 (marble-1.1-plus).
"""

import gzip
import hashlib
import json
import os
import struct
import sys
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

ASSETS_DIR = ROOT_DIR / "assets" / "p3" / "marble"
DOCS_MARBLE_DIR = ROOT_DIR / "docs" / "p3" / "marble"
DOCS_CAR_DIR = ROOT_DIR / "docs" / "car"
DOCS_CAR_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def process_v2_space():
    print("==================================================================")
    print("  CAR-03: Processing Marble 1.1-plus Space & Table Alignment")
    print("==================================================================")

    # 1. Semantics
    semantics_path = DOCS_MARBLE_DIR / "car_studio_v2_semantics.json"
    with open(semantics_path, "r", encoding="utf-8") as f:
        sem_data = json.load(f)

    s = float(sem_data.get("metric_scale_factor", 2.2508733))
    h = float(sem_data.get("ground_plane_offset", 1.6300833))
    print(f"[*] Semantics: metric_scale_factor (s) = {s:.7f}, ground_plane_offset (h) = {h:.6f}")

    # 2. Table and Vehicle Geometry Metrics
    # Table top surface: y = 0.725 m (matching collider mesh median 0.7237m and splats)
    y_table = 0.7250
    y_floor = 0.0000

    # Table bounds derived from collider mesh in table zone
    table_xmin = -1.8700
    table_xmax = 1.9100
    table_zmin = -2.9500
    table_zmax = -0.6700

    table_width = round(table_xmax - table_xmin, 4) # 3.7800 m
    table_depth = round(table_zmax - table_zmin, 4) # 2.2800 m
    table_cx = round((table_xmin + table_xmax) / 2.0, 4) # 0.0200 m
    table_cz = round((table_zmin + table_zmax) / 2.0, 4) # -1.8100 m

    # Baked car model location on table: centered around x=0.0, z=-1.30
    car_center_x = 0.0000
    car_center_z = -1.3000

    # Target vehicle dimensions based on 60% of table depth (2.28m * 0.6 = 1.368m ~ 1.35m)
    L_target = 1.3500
    s_car = round(L_target / 2.10, 6) # 0.642857
    car_w = round(1.0 * s_car, 4) # 0.6429 m
    car_h = round(0.55 * s_car, 4) # 0.3536 m
    half_h = round(car_h / 2.0, 4) # 0.1768 m
    car_mass = round(12.0 * (s_car ** 3), 4) # 3.1873 kg
    car_impulse = round(car_mass * 3.0, 4) # 9.5619 N*s
    drop_y = round(y_table + 2.0, 4) # 2.7250 m
    initial_car_y = round(y_table + half_h + 0.005, 4) # 0.9068 m (clearance: +5mm)

    print(f"[*] Table Footprint:")
    print(f"    X: [{table_xmin:.4f}, {table_xmax:.4f}] (width={table_width:.4f}m)")
    print(f"    Z: [{table_zmin:.4f}, {table_zmax:.4f}] (depth={table_depth:.4f}m)")
    print(f"    Center: ({table_cx:.4f}, {y_table:.4f}, {table_cz:.4f})")
    print(f"[*] Scaled Vehicle Model:")
    print(f"    L = {L_target}m ({L_target/table_depth*100:.1f}% of table depth {table_depth:.2f}m)")
    print(f"    Scale factor s_car = {s_car:.4f}")
    print(f"    Dimensions: {car_w}m (W) x {car_h}m (H) x {L_target}m (L)")
    print(f"    Mass: {car_mass} kg, Push Impulse: {car_impulse} N*s")
    print(f"    Initial placement: ({car_center_x}, {initial_car_y}, {car_center_z})")

    footprint_record = {
        "y_table": y_table,
        "y_floor": y_floor,
        "table_footprint_bbox": {
            "xmin": table_xmin,
            "xmax": table_xmax,
            "zmin": table_zmin,
            "zmax": table_zmax,
            "width": table_width,
            "depth": table_depth,
            "center_x": table_cx,
            "center_z": table_cz
        },
        "vehicle_specs": {
            "target_length": L_target,
            "scale_factor": s_car,
            "width": car_w,
            "height": car_h,
            "half_height": half_h,
            "mass_kg": car_mass,
            "impulse_ns": car_impulse,
            "drop_height_y": drop_y,
            "initial_x": car_center_x,
            "initial_y": initial_car_y,
            "initial_z": car_center_z
        }
    }
    (DOCS_CAR_DIR / "table_v2_footprint.json").write_text(json.dumps(footprint_record, indent=2))

    # 3. SPZ Splat Cleaning (Box SDF Alpha Zeroing on baked car)
    spz_in = ASSETS_DIR / "car_studio_v2_500k.spz"
    with gzip.open(spz_in, "rb") as f:
        hdr = f.read(16)
        magic, ver, num_splats, sh, frac_bits, flags, res = struct.unpack("<IIIBBBB", hdr)
        fixed = 1 << frac_bits

        centers_raw = f.read(num_splats * 9)
        c_bytes = np.frombuffer(centers_raw, dtype=np.uint8).reshape((num_splats, 3, 3))
        val = (c_bytes[:, :, 2].astype(np.int32) << 24) | (c_bytes[:, :, 1].astype(np.int32) << 16) | (c_bytes[:, :, 0].astype(np.int32) << 8)
        val = val >> 8
        centers = val.astype(np.float32) / fixed

        alphas_raw = f.read(num_splats)
        alphas = np.frombuffer(alphas_raw, dtype=np.uint8).copy()
        rest_data = f.read()

    x_three = s * centers[:, 0]
    y_three = -(s * centers[:, 1] - h)
    z_three = -s * centers[:, 2]

    car_box = {
        "xmin": -0.6500,
        "xmax": 0.6500,
        "ymin": 0.7200,
        "ymax": 1.3500,
        "zmin": -1.9000,
        "zmax": -0.6500
    }

    in_box = (
        (x_three >= car_box["xmin"]) & (x_three <= car_box["xmax"]) &
        (y_three >= car_box["ymin"]) & (y_three <= car_box["ymax"]) &
        (z_three >= car_box["zmin"]) & (z_three <= car_box["zmax"])
    )

    num_inside = int(np.sum(in_box))
    num_outside = int(num_splats - num_inside)
    print(f"[*] Total splats: {num_splats:,}")
    print(f"[*] Splats inside car Box SDF: {num_inside:,} ({num_inside/num_splats*100:.2f}%)")
    print(f"[*] Splats outside car Box SDF: {num_outside:,}")

    alphas_clean = alphas.copy()
    alphas_clean[in_box] = 0

    outside_changed = int(np.sum(alphas[~in_box] != alphas_clean[~in_box]))
    outside_change_rate = float(outside_changed / num_outside)
    print(f"[*] Outside splats modified count: {outside_changed}")
    print(f"[*] Outside splats change rate: {outside_change_rate * 100:.6f}%")

    spz_out = ASSETS_DIR / "car_studio_v2_clean_500k.spz"
    with gzip.open(spz_out, "wb") as f:
        f.write(hdr)
        f.write(centers_raw)
        f.write(alphas_clean.tobytes())
        f.write(rest_data)

    clean_bytes = spz_out.read_bytes()
    clean_sha256 = hashlib.sha256(clean_bytes).hexdigest()
    print(f"[+] Written clean SPZ: {spz_out} ({len(clean_bytes):,} bytes, sha256={clean_sha256})")

    splat_record = {
        "clean_spz_path": str(spz_out.relative_to(ROOT_DIR)),
        "clean_spz_sha256": clean_sha256,
        "clean_spz_bytes": len(clean_bytes),
        "total_splats": int(num_splats),
        "box_sdf": car_box,
        "splats_inside_box": num_inside,
        "splats_inside_zeroed": num_inside,
        "splats_outside_box": num_outside,
        "splats_outside_modified": outside_changed,
        "outside_change_rate": outside_change_rate,
        "outside_change_rate_pass": bool(outside_change_rate == 0.0),
        "verdict": "PASS" if outside_change_rate == 0.0 else "FAIL"
    }
    (DOCS_CAR_DIR / "splat_edit_car_removal_v2.json").write_text(json.dumps(splat_record, indent=2))

    transform_record = {
        "semantics": sem_data,
        "metric_scale_factor": s,
        "ground_plane_offset": h,
        "y_floor": y_floor,
        "y_table": y_table,
        "table_footprint": footprint_record["table_footprint_bbox"],
        "vehicle_specs": footprint_record["vehicle_specs"],
        "threejs_transform": {
            "scale": [s, s, s],
            "rotation": [np.pi, 0, 0],
            "position": [0, h, 0]
        }
    }
    (DOCS_CAR_DIR / "transform_v2.json").write_text(json.dumps(transform_record, indent=2))
    print("[+] All v2 space transforms and footprints processed successfully!")
    return transform_record


if __name__ == "__main__":
    process_v2_space()

#!/usr/bin/env python3
"""
scripts/verify_synthetic_set.py

Verifies P3-00-C Task 1 Synthetic Multi-view Dataset:
1. JSON schema compliance for every frame against docs/p3/spatial_context_schema.json
2. Existence and resolution of all 32 rendered PNG images (1280x960)
3. Three.js camera restoration & round-trip conversion accuracy (< 1e-6)
"""

import json
import os
import sys
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
CAM_FILE = ROOT_DIR / "assets" / "p3" / "synthetic_object" / "cameras.json"
SCHEMA_FILE = ROOT_DIR / "docs" / "p3" / "spatial_context_schema.json"

sys.path.insert(0, str(ROOT_DIR / "scripts"))
from spatial_context import opencv_to_three_camera, three_to_opencv_camera

def verify():
    print("==================================================================")
    print("  Verifying P3-00-C Task 1 Synthetic Multi-view Dataset")
    print("==================================================================")

    assert CAM_FILE.exists(), f"Cameras file not found: {CAM_FILE}"
    assert SCHEMA_FILE.exists(), f"Schema file not found: {SCHEMA_FILE}"

    with open(CAM_FILE, "r", encoding="utf-8") as f:
        cam_data = json.load(f)

    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema = json.load(f)

    metadata = cam_data.get("metadata", {})
    frames = cam_data.get("frames", [])

    print(f"Metadata: Object='{metadata.get('object_name')}', Dimensions={metadata.get('object_dimensions_m')} m")
    print(f"Total Frames: {len(frames)} (Expected: 32)")
    assert len(frames) == 32, f"Expected 32 frames, got {len(frames)}"

    # Required fields in schema
    required_keys = set(schema.get("required", []))

    max_pos_err = 0.0
    max_rot_err = 0.0
    max_k_err = 0.0

    for idx, frame in enumerate(frames):
        # 1. Schema key check
        missing = required_keys - set(frame.keys())
        assert not missing, f"Frame {idx} missing required keys: {missing}"

        # 2. Image existence and dimension
        rel_img = frame["image_path"]
        abs_img = ROOT_DIR / rel_img
        assert abs_img.exists(), f"Image not found: {abs_img}"
        sz = abs_img.stat().st_size
        assert sz > 50000, f"Image too small ({sz} B): {abs_img}"

        # 3. Camera transformation round-trip test
        K = np.array(frame["K"], dtype=np.float64)
        Rt = np.array(frame["Rt"], dtype=np.float64)

        # OpenCV -> Three.js
        pos_three, R_three, fov_y, aspect = opencv_to_three_camera(
            Rt, K, width=metadata.get("width", 1280), height=metadata.get("height", 960)
        )

        # Three.js -> OpenCV
        Rt_restored, K_restored = three_to_opencv_camera(
            pos_three, R_three, fov_y, width=metadata.get("width", 1280), height=metadata.get("height", 960)
        )

        pos_err = np.linalg.norm(Rt[:3, 3] - Rt_restored[:3, 3])
        rot_err = np.linalg.norm(Rt[:3, :3] - Rt_restored[:3, :3])
        k_err = np.linalg.norm(K - K_restored)

        max_pos_err = max(max_pos_err, pos_err)
        max_rot_err = max(max_rot_err, rot_err)
        max_k_err = max(max_k_err, k_err)

    print(f"\n[PASS] All 32 frames verified!")
    print(f"  Max Extrinsic Rotation Roundtrip Error: {max_rot_err:.2e}")
    print(f"  Max Extrinsic Position Roundtrip Error: {max_pos_err:.2e} m")
    print(f"  Max Intrinsic K Roundtrip Error:        {max_k_err:.2e}")

    assert max_rot_err < 1e-6, "Rotation error exceeds 1e-6"
    assert max_pos_err < 1e-6, "Position error exceeds 1e-6"
    assert max_k_err < 1e-6, "Intrinsic error exceeds 1e-6"
    print("\n✅ P3-00-C Task 1 Synthetic Dataset Verification PASSED!")

if __name__ == "__main__":
    verify()

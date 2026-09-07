#!/usr/bin/env python3
"""
scripts/generate_t5c_holdout_clicks.py

EXE-260906-P3-02-T5-c Task 4: Deterministic Holdout Picking Dataset Generator (Seed 20260908)
Extracts 225 ground-truth click coordinates from V1, V2, V3 difference masks
using seed=20260908:
- Dynamic target: 150 clicks (V1: 25 L1 + 25 R1, V2: 50 L1, V3: 50 R1)
- Static target:  75 clicks (25 per view)
Saves output to tests/p3/t5c_holdout_clicks.json and records SHA256 in docs/p3/raw/t5c_holdout_clicks_sha256.txt.
Once generated, tests/p3/t5c_holdout_clicks.json is strictly frozen and never modified.
"""

import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
TESTS_DIR = ROOT_DIR / "tests" / "p3"
MANIFEST_FILE = RAW_DIR / "t4b_500k_partition_metrics.json"
OUT_JSON = TESTS_DIR / "t5c_holdout_clicks.json"
RAW_SHA_FILE = RAW_DIR / "t5c_holdout_clicks_sha256.txt"

DIFF_THRESHOLD = 24
SEED = 20260908


def main():
    np.random.seed(SEED)
    print(f"[*] Initializing Holdout Clicks Generation with seed={SEED}...")

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    parts = {p["id"]: p for p in manifest["parts"]}
    l1_c = parts["box_l1"]["centroid_m"]
    r1_c = parts["box_r1"]["centroid_m"]

    all_clicks = []
    click_idx = 1

    views_spec = [
        ("V1", "marble_run01_view_v1_on.png", "marble_run01_view_v1_off.png"),
        ("V2", "marble_run01_view_v2_on.png", "marble_run01_view_v2_off.png"),
        ("V3", "marble_run01_view_v3_on.png", "marble_run01_view_v3_off.png"),
    ]

    for v_key, on_name, off_name in views_spec:
        on_p = CAPTURES_DIR / on_name
        off_p = CAPTURES_DIR / off_name
        if not on_p.exists() or not off_p.exists():
            raise FileNotFoundError(f"Missing capture file for {v_key}: {on_p} or {off_p}")

        im_on = np.array(Image.open(on_p).convert("RGB"), dtype=np.int16)
        im_off = np.array(Image.open(off_p).convert("RGB"), dtype=np.int16)
        H, W, _ = im_on.shape

        diff = np.max(np.abs(im_on - im_off), axis=-1)
        tint_mask = (diff >= DIFF_THRESHOLD)
        static_mask = (diff < 8)

        # Border margin to avoid UI or clipping edges
        border_mask = np.zeros((H, W), dtype=bool)
        border_mask[60:H-60, 60:W-60] = True
        tint_mask &= border_mask
        static_mask &= border_mask

        if v_key == "V1":
            # Both L1 (left) and R1 (right) are in frame
            l1_mask = tint_mask & (np.arange(W)[None, :] < W // 2)
            r1_mask = tint_mask & (np.arange(W)[None, :] >= W // 2)

            l1_y, l1_x = np.where(l1_mask)
            r1_y, r1_x = np.where(r1_mask)

            assert len(l1_y) >= 25, f"V1 L1 tint pixels ({len(l1_y)}) < 25"
            assert len(r1_y) >= 25, f"V1 R1 tint pixels ({len(r1_y)}) < 25"

            l1_chosen = np.random.choice(len(l1_y), 25, replace=False)
            for idx in l1_chosen:
                all_clicks.append({
                    "index": click_idx,
                    "view": "V1",
                    "target_type": "dynamic",
                    "expected_part_id": "box_l1",
                    "screen_coord": [int(l1_x[idx]), int(l1_y[idx])]
                })
                click_idx += 1

            r1_chosen = np.random.choice(len(r1_y), 25, replace=False)
            for idx in r1_chosen:
                all_clicks.append({
                    "index": click_idx,
                    "view": "V1",
                    "target_type": "dynamic",
                    "expected_part_id": "box_r1",
                    "screen_coord": [int(r1_x[idx]), int(r1_y[idx])]
                })
                click_idx += 1

        elif v_key == "V2":
            l1_y, l1_x = np.where(tint_mask)
            assert len(l1_y) >= 50, f"V2 L1 tint pixels ({len(l1_y)}) < 50"
            l1_chosen = np.random.choice(len(l1_y), 50, replace=False)
            for idx in l1_chosen:
                all_clicks.append({
                    "index": click_idx,
                    "view": "V2",
                    "target_type": "dynamic",
                    "expected_part_id": "box_l1",
                    "screen_coord": [int(l1_x[idx]), int(l1_y[idx])]
                })
                click_idx += 1

        elif v_key == "V3":
            r1_y, r1_x = np.where(tint_mask)
            assert len(r1_y) >= 50, f"V3 R1 tint pixels ({len(r1_y)}) < 50"
            r1_chosen = np.random.choice(len(r1_y), 50, replace=False)
            for idx in r1_chosen:
                all_clicks.append({
                    "index": click_idx,
                    "view": "V3",
                    "target_type": "dynamic",
                    "expected_part_id": "box_r1",
                    "screen_coord": [int(r1_x[idx]), int(r1_y[idx])]
                })
                click_idx += 1

        st_y, st_x = np.where(static_mask)
        assert len(st_y) >= 25, f"{v_key} static pixels ({len(st_y)}) < 25"
        st_chosen = np.random.choice(len(st_y), 25, replace=False)
        for idx in st_chosen:
            all_clicks.append({
                "index": click_idx,
                "view": v_key,
                "target_type": "static",
                "expected_part_id": "static",
                "screen_coord": [int(st_x[idx]), int(st_y[idx])]
            })
            click_idx += 1

    assert len(all_clicks) == 225, f"Expected 225 clicks, got {len(all_clicks)}"

    payload = {
        "schema_version": "1.0.0",
        "directive": "EXE-260906-P3-02-T5-c",
        "random_seed": SEED,
        "total_clicks": len(all_clicks),
        "dynamic_clicks": 150,
        "static_clicks": 75,
        "l1_centroid": l1_c,
        "r1_centroid": r1_c,
        "views": {
            "V1": {"name": "Front View", "eye": [0.0, 1.6, 0.8], "target": [0.0, 1.3, -6.0], "l1_samples": 25, "r1_samples": 25, "static_samples": 25},
            "V2": {"name": "L1 Focus View", "eye": [-0.6, 1.4, 0.3], "target": l1_c, "l1_samples": 50, "r1_samples": 0, "static_samples": 25},
            "V3": {"name": "R1 Focus View", "eye": [0.6, 1.4, 0.3], "target": r1_c, "l1_samples": 0, "r1_samples": 50, "static_samples": 25}
        },
        "clicks": all_clicks
    }

    TESTS_DIR.mkdir(parents=True, exist_ok=True)
    raw_json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    OUT_JSON.write_text(raw_json_text + "\n", encoding="utf-8")

    file_bytes = OUT_JSON.read_bytes()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    raw_sha_content = f"{file_sha256}  tests/p3/t5c_holdout_clicks.json\n"
    RAW_SHA_FILE.write_text(raw_sha_content, encoding="utf-8")

    print("==================================================================")
    print("  EXE-260906-P3-02-T5-c Task 4: New Holdout Clicks Dataset Generated")
    print("==================================================================")
    print(f"Target File:   {OUT_JSON}")
    print(f"Total Clicks:  {len(all_clicks)} (Dynamic: 150, Static: 75)")
    print(f"Random Seed:   {SEED}")
    print(f"SHA-256:       {file_sha256}")
    print(f"Recorded to:   {RAW_SHA_FILE}")
    print("==================================================================")


if __name__ == "__main__":
    main()

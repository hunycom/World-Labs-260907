#!/usr/bin/env python3
"""
scripts/generate_smoke_clicks.py

Generates 20 smoke test click coordinates (seed=20260907) that are strictly
non-overlapping with tests/p3/t5_holdout_clicks.json:
- 5 L1 clicks (2 V1 + 3 V2, bounded to part screen extent)
- 5 R1 clicks (2 V1 + 3 V3, bounded to part screen extent)
- 10 Static clicks (4 V1 + 3 V2 + 3 V3)
Saves output to tests/p3/t5b_smoke_clicks.json.
"""

import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
HOLDOUT_JSON = ROOT_DIR / "tests" / "p3" / "t5_holdout_clicks.json"
OUT_JSON = ROOT_DIR / "tests" / "p3" / "t5b_smoke_clicks.json"

DIFF_THRESHOLD = 24
SEED = 20260907


def main():
    np.random.seed(SEED)
    print(f"[*] Initializing Smoke Clicks Generation with seed={SEED}...")

    if not HOLDOUT_JSON.exists():
        raise FileNotFoundError(f"Holdout file missing: {HOLDOUT_JSON}")

    holdout_data = json.loads(HOLDOUT_JSON.read_text(encoding="utf-8"))
    all_holdout_coords = set((c["view"], tuple(c["screen_coord"])) for c in holdout_data["clicks"])

    smoke_clicks = []
    idx = 1

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

        border_mask = np.zeros((H, W), dtype=bool)
        border_mask[60:H-60, 60:W-60] = True
        tint_mask &= border_mask
        static_mask &= border_mask

        # Exclude any coordinates already in holdout
        for (hv, hcoord) in all_holdout_coords:
            if hv == v_key:
                hx, hy = hcoord
                if 0 <= hy < H and 0 <= hx < W:
                    tint_mask[hy, hx] = False
                    static_mask[hy, hx] = False

        if v_key == "V1":
            # Bbox bounded for L1: [120, 440] x [500, 700]
            l1_mask = tint_mask.copy()
            l1_crop = np.zeros((H, W), dtype=bool)
            l1_crop[500:700, 120:440] = True
            l1_mask &= l1_crop

            # Bbox bounded for R1: [880, 1130] x [500, 700]
            r1_mask = tint_mask.copy()
            r1_crop = np.zeros((H, W), dtype=bool)
            r1_crop[500:700, 880:1130] = True
            r1_mask &= r1_crop

            l1_y, l1_x = np.where(l1_mask)
            r1_y, r1_x = np.where(r1_mask)

            for i in np.random.choice(len(l1_y), 2, replace=False):
                coord = [int(l1_x[i]), int(l1_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "dynamic",
                    "expected_part_id": "box_l1",
                    "screen_coord": coord
                })
                idx += 1

            for i in np.random.choice(len(r1_y), 2, replace=False):
                coord = [int(r1_x[i]), int(r1_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "dynamic",
                    "expected_part_id": "box_r1",
                    "screen_coord": coord
                })
                idx += 1

            st_y, st_x = np.where(static_mask)
            for i in np.random.choice(len(st_y), 4, replace=False):
                coord = [int(st_x[i]), int(st_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "static",
                    "expected_part_id": "static",
                    "screen_coord": coord
                })
                idx += 1

        elif v_key == "V2":
            # Bbox bounded for L1 in V2: [560, 880] x [240, 510]
            l1_mask = tint_mask.copy()
            l1_crop = np.zeros((H, W), dtype=bool)
            l1_crop[240:510, 560:880] = True
            l1_mask &= l1_crop

            l1_y, l1_x = np.where(l1_mask)
            for i in np.random.choice(len(l1_y), 3, replace=False):
                coord = [int(l1_x[i]), int(l1_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "dynamic",
                    "expected_part_id": "box_l1",
                    "screen_coord": coord
                })
                idx += 1

            st_y, st_x = np.where(static_mask)
            for i in np.random.choice(len(st_y), 3, replace=False):
                coord = [int(st_x[i]), int(st_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "static",
                    "expected_part_id": "static",
                    "screen_coord": coord
                })
                idx += 1

        elif v_key == "V3":
            # Bbox bounded for R1 in V3: [450, 720] x [250, 470]
            r1_mask = tint_mask.copy()
            r1_crop = np.zeros((H, W), dtype=bool)
            r1_crop[250:470, 450:720] = True
            r1_mask &= r1_crop

            r1_y, r1_x = np.where(r1_mask)
            for i in np.random.choice(len(r1_y), 3, replace=False):
                coord = [int(r1_x[i]), int(r1_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "dynamic",
                    "expected_part_id": "box_r1",
                    "screen_coord": coord
                })
                idx += 1

            st_y, st_x = np.where(static_mask)
            for i in np.random.choice(len(st_y), 3, replace=False):
                coord = [int(st_x[i]), int(st_y[i])]
                assert (v_key, tuple(coord)) not in all_holdout_coords
                smoke_clicks.append({
                    "index": idx,
                    "view": v_key,
                    "target_type": "static",
                    "expected_part_id": "static",
                    "screen_coord": coord
                })
                idx += 1

    assert len(smoke_clicks) == 20
    overlap = sum(1 for c in smoke_clicks if (c["view"], tuple(c["screen_coord"])) in all_holdout_coords)
    assert overlap == 0, f"Found {overlap} overlapping coordinates with holdout!"

    payload = {
        "schema_version": "1.0.0",
        "directive": "EXE-260906-P3-02-T5-b",
        "random_seed": SEED,
        "total_clicks": len(smoke_clicks),
        "dynamic_clicks": 10,
        "static_clicks": 10,
        "holdout_overlap_count": 0,
        "clicks": smoke_clicks
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[+] Saved 20 smoke clicks to {OUT_JSON} (Overlap with holdout: 0)")


if __name__ == "__main__":
    main()

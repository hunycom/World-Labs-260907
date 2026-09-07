#!/usr/bin/env python3
"""
scripts/measure_glow_ratio.py

EXE-260906-P3-02-T4B-R3 Task 2: Exclusive Hue Glow Outside Ratio Measurement
Quantifies color bleed / glow outside the 2D projected bounding box for all 6 dynamic parts.
Compares Round 1 (SplatEdit SDF Box) vs Round 3 (Discrete Multi-SplatMesh T4B-R3).

Algorithm (Mutually Exclusive Nearest Target Hue):
1. Convert image RGB (1280x720) to HSV: Hue in [0, 360), Saturation in [0, 1], Value in [0, 1].
2. For each pixel:
   - Filter by Saturation: S >= 0.35
   - Calculate angular distance to each of the 6 target hues:
       diff_k = min(|H - target_k|, 360 - |H - target_k|)
   - Find nearest target hue: min_diff = min_k(diff_k), best_k = argmin_k(diff_k)
   - Assign to part k iff (S >= 0.35) and (min_diff <= 20.0 deg) and (best_k == k).
   - Each pixel is exclusively assigned to at most ONE part.
3. For each part:
   - Inside pixels: mask & projected 2D bbox (p5-p95 with 3cm margin)
   - Outside pixels: mask & (~projected 2D bbox)
   - Total pixels = inside + outside
   - Outside ratio = (outside / total) * 100%
   - Verdict: PASS if ratio < 15.0%, else 미달 (ratio%)
"""

import argparse
import json
import sys
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
ROUND1_DIR = CAPTURES_DIR / "round1_backup"
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
MANIFEST_FILE = RAW_DIR / "t4b_r3_500k_partition_metrics.json"

CAM_POS = np.array([0.0, 1.6, 0.8], dtype=np.float64)
CAM_TARGET = np.array([0.0, 1.3, -6.0], dtype=np.float64)
FOV_DEG = 60.0
IMG_W = 1280
IMG_H = 720
ASPECT = IMG_W / IMG_H

TARGET_HUES = {
    "box_l1": 183.53,  # Cyan (#00f0ff)
    "box_r1": 36.00,   # Orange (#ff9900)
    "box_l2": 160.12,  # Emerald Green (#10b981)
    "box_r2": 349.72,  # Rose Red (#f43f5e)
    "box_l3": 270.74,  # Purple (#a855f7)
    "box_r3": 45.40,   # Yellow (#eab308)
}

forward = (CAM_TARGET - CAM_POS) / np.linalg.norm(CAM_TARGET - CAM_POS)
up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
right = np.cross(forward, up)
right /= np.linalg.norm(right)
true_up = np.cross(right, forward)
tan_half_fov = np.tan(np.radians(FOV_DEG / 2.0))


def project_pt(pt: np.ndarray):
    rel = pt - CAM_POS
    xc = float(np.dot(rel, right))
    yc = float(np.dot(rel, true_up))
    zc = float(np.dot(rel, forward))
    if zc <= 0:
        return None
    nx = xc / (zc * tan_half_fov * ASPECT)
    ny = yc / (zc * tan_half_fov)
    u = (nx + 1.0) * 0.5 * IMG_W
    v = (1.0 - (ny + 1.0) * 0.5) * IMG_H
    return u, v


def get_projected_bbox_2d(p5: list, p95: list, margin: float = 0.03):
    bmin = np.array(p5, dtype=np.float64) - margin
    bmax = np.array(p95, dtype=np.float64) + margin
    corners = []
    for x in [bmin[0], bmax[0]]:
        for y in [bmin[1], bmax[1]]:
            for z in [bmin[2], bmax[2]]:
                proj = project_pt(np.array([x, y, z]))
                if proj is not None:
                    corners.append(proj)
    if not corners:
        return 0, 0, 0, 0
    corners = np.array(corners)
    u_min = max(0, int(np.floor(corners[:, 0].min())) - 2)
    u_max = min(IMG_W, int(np.ceil(corners[:, 0].max())) + 2)
    v_min = max(0, int(np.floor(corners[:, 1].min())) - 2)
    v_max = min(IMG_H, int(np.ceil(corners[:, 1].max())) + 2)
    return u_min, u_max, v_min, v_max


def rgb_to_hsv_deg(rgb: np.ndarray):
    """
    Vectorized RGB to HSV conversion.
    rgb: uint8 array (H, W, 3) in [0, 255]
    returns: h in [0, 360), s in [0, 1], v in [0, 1]
    """
    arr = rgb.astype(np.float32) / 255.0
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    maxc = np.maximum(np.maximum(r, g), b)
    minc = np.minimum(np.minimum(r, g), b)
    v = maxc
    deltac = maxc - minc

    s = np.zeros_like(v)
    nonzero_v = v > 1e-6
    s[nonzero_v] = deltac[nonzero_v] / v[nonzero_v]

    h = np.zeros_like(v)
    nonzero_d = deltac > 1e-6

    rc = (maxc - r) / np.where(nonzero_d, deltac, 1.0)
    gc = (maxc - g) / np.where(nonzero_d, deltac, 1.0)
    bc = (maxc - b) / np.where(nonzero_d, deltac, 1.0)

    mask_r = nonzero_d & (r == maxc)
    mask_g = nonzero_d & (g == maxc) & (~mask_r)
    mask_b = nonzero_d & (b == maxc) & (~mask_r) & (~mask_g)

    h[mask_r] = (bc[mask_r] - gc[mask_r]) % 6.0
    h[mask_g] = 2.0 + rc[mask_g] - bc[mask_g]
    h[mask_b] = 4.0 + gc[mask_b] - rc[mask_b]

    h = (h / 6.0) * 360.0 % 360.0
    return h, s, v


def compute_exclusive_part_masks(im: np.ndarray, part_ids: list[str]) -> dict[str, np.ndarray]:
    h, s, v = rgb_to_hsv_deg(im)
    s_mask = s >= 0.35

    diffs = []
    for pid in part_ids:
        th = TARGET_HUES[pid]
        d = np.abs(h - th)
        d = np.minimum(d, 360.0 - d)
        diffs.append(d)
    diff_stack = np.stack(diffs, axis=-1)  # (H, W, num_parts)

    min_diff = np.min(diff_stack, axis=-1)  # (H, W)
    best_idx = np.argmin(diff_stack, axis=-1)  # (H, W)

    masks = {}
    for i, pid in enumerate(part_ids):
        masks[pid] = s_mask & (min_diff <= 20.0) & (best_idx == i)
    return masks


def main():
    r1_img = ROUND1_DIR / "marble_run01_part_front.png"
    r3_img = CAPTURES_DIR / "marble_run01_part_front.png"

    if not r1_img.exists():
        print(f"[ERROR] Round 1 image not found: {r1_img}", file=sys.stderr)
        sys.exit(1)
    if not r3_img.exists():
        print(f"[ERROR] Round 3 image not found: {r3_img}", file=sys.stderr)
        sys.exit(1)

    r1_im = np.array(Image.open(r1_img).convert("RGB"))
    r3_im = np.array(Image.open(r3_img).convert("RGB"))
    r1_sha = hashlib.sha256(r1_img.read_bytes()).hexdigest()
    r3_sha = hashlib.sha256(r3_img.read_bytes()).hexdigest()

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    parts_meta = manifest.get("parts", [])
    dynamic_parts = [p for p in parts_meta if p.get("type") == "dynamic"]
    part_ids = [p["id"] for p in dynamic_parts]

    bboxes_2d = {}
    for p in dynamic_parts:
        p5 = p["bounding_box_p5_p95"]["min"]
        p95 = p["bounding_box_p5_p95"]["max"]
        margin = p.get("margin_m", 0.03)
        bboxes_2d[p["id"]] = get_projected_bbox_2d(p5, p95, margin)

    # Compute mutually exclusive masks
    r1_masks = compute_exclusive_part_masks(r1_im, part_ids)
    r3_masks = compute_exclusive_part_masks(r3_im, part_ids)

    print("==================================================================")
    print("  EXE-260906-P3-02-T4B-R3 Task 2: Exclusive Hue Glow Outside Ratio")
    print("==================================================================")
    print(f"Round 1 Image (SplatEdit SDF):         {r1_img.name} (SHA: {r1_sha[:16]}...)")
    print(f"Round 3 Image (Discrete Multi-SplatMesh): {r3_img.name} (SHA: {r3_sha[:16]}...)")
    print("Criteria: Outside Glow Ratio < 15.0% (Full Frame Spec)\n")

    results_data = {
        "directive": "EXE-260906-P3-02-T4B-R3",
        "round1_sha256": r1_sha,
        "round3_sha256": r3_sha,
        "target_hues_deg": TARGET_HUES,
        "parts": {}
    }

    print("#### Full Frame (1280x720, 상호배타 색상각거리 <= 20.0 deg, S >= 0.35) 발광 비율 측정 결과")
    print("| 부품 ID | 명칭 | 색상 (각도) | 1차 총픽셀 | 1차 밖 | 1차 비율 | 3차 총픽셀 | 3차 밖 | 3차 비율 | 판정 (<15.0%) |")
    print("|---|---|---|---|---|---|---|---|---|---|")

    full_pass_count = 0
    for p in dynamic_parts:
        pid = p["id"]
        u0, u1, v0, v1 = bboxes_2d[pid]

        in_box = np.zeros((IMG_H, IMG_W), dtype=bool)
        in_box[v0:v1, u0:u1] = True

        m1 = r1_masks[pid]
        t1 = int(np.sum(m1))
        i1 = int(np.sum(m1 & in_box))
        o1 = int(np.sum(m1 & (~in_box)))
        r1 = (o1 / t1 * 100.0) if t1 > 0 else 0.0

        m3 = r3_masks[pid]
        t3 = int(np.sum(m3))
        i3 = int(np.sum(m3 & in_box))
        o3 = int(np.sum(m3 & (~in_box)))
        r3 = (o3 / t3 * 100.0) if t3 > 0 else 0.0

        pass_full = (r3 < 15.0)
        if pass_full:
            full_pass_count += 1
        verdict = "PASS" if pass_full else f"미달 ({r3:.1f}%)"
        th_str = f"{TARGET_HUES[pid]:.1f}°"
        print(f"| `{pid}` | {p['name_en']} | {th_str} | {t1:6,d} | {o1:6,d} | {r1:5.1f}% | {t3:6,d} | {o3:6,d} | {r3:5.1f}% | **{verdict}** |")

        results_data["parts"][pid] = {
            "name": p["name_en"],
            "target_hue_deg": TARGET_HUES[pid],
            "bbox_2d": [u0, u1, v0, v1],
            "round1": {"total": t1, "inside": i1, "outside": o1, "ratio_pct": round(r1, 2)},
            "round3": {"total": t3, "inside": i3, "outside": o3, "ratio_pct": round(r3, 2)},
            "pass": pass_full
        }

    print(f"\nFull Frame 통과율: {full_pass_count}/6 부품\n")
    print("==================================================================")

    # Save raw outputs
    out_json = RAW_DIR / "t4b_r3_glow.json"
    out_json.write_text(json.dumps(results_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[*] Saved structured JSON to: {out_json}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
scripts/analyze_color_hist.py

EXE-260906-P3-02-T4B-R2 Task 2: RGB Histogram & Inside Pixel Analysis
Analyzes RGB clusters inside each part's 2D projected bounding box.
Evaluates why initial 1st round thresholds failed for distant parts.
Demonstrates that refined thresholds capture >= 500 pixels inside all 6 bounding boxes.
"""

import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from collections import Counter

ROOT_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
MANIFEST_FILE = RAW_DIR / "t4b_500k_partition_metrics.json"

CAM_POS = np.array([0.0, 1.6, 0.8], dtype=np.float64)
CAM_TARGET = np.array([0.0, 1.3, -6.0], dtype=np.float64)
FOV_DEG = 60.0
IMG_W = 1280
IMG_H = 720
ASPECT = IMG_W / IMG_H

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


def get_color_mask(im: np.ndarray, pid: str) -> np.ndarray:
    R = im[:, :, 0].astype(np.int32)
    G = im[:, :, 1].astype(np.int32)
    B = im[:, :, 2].astype(np.int32)
    if pid == "box_l1":
        return (G >= 100) & (B >= 120) & (B > R + 40) & (G > R + 40)
    elif pid == "box_r1":
        return (R >= 160) & (G >= 70) & (R > B + 80) & (R > G + 30)
    elif pid == "box_l2":
        return (G >= 90) & (G > R + 25) & (G > B + 10)
    elif pid == "box_r2":
        return (R >= 120) & (R > G + 35) & (R > B + 20)
    elif pid == "box_l3":
        return (B >= 90) & (R >= 70) & (B > G + 20) & (R > G + 15)
    elif pid == "box_r3":
        return (R >= 110) & (G >= 80) & (B < 60) & (R > B + 40) & (G > B + 20)
    return np.zeros((im.shape[0], im.shape[1]), dtype=bool)


def main():
    img_path = CAPTURES_DIR / "marble_run01_part_front.png"
    if not img_path.exists():
        print(f"[ERROR] Capture image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    im = np.array(Image.open(img_path).convert("RGB"))
    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))

    print("==================================================================")
    print("  EXE-260906-P3-02-T4B-R2 Task 2: RGB Histogram & Inside Pixels")
    print("==================================================================")
    print(f"Target Image: {img_path.name}")
    print("Verification Criterion: Inside Detected Pixels >= 500 px for all 6 parts\n")

    summary_rows = []

    for p in manifest["parts"]:
        if p["type"] != "dynamic":
            continue
        pid = p["id"]
        p5 = p["bounding_box_p5_p95"]["min"]
        p95 = p["bounding_box_p5_p95"]["max"]
        margin = p.get("margin_m", 0.03)

        bmin = np.array(p5) - margin
        bmax = np.array(p95) + margin
        corners = []
        for x in [bmin[0], bmax[0]]:
            for y in [bmin[1], bmax[1]]:
                for z in [bmin[2], bmax[2]]:
                    proj = project_pt(np.array([x, y, z]))
                    if proj:
                        corners.append(proj)
        corners = np.array(corners)
        u0 = max(0, int(np.floor(corners[:, 0].min())) - 2)
        u1 = min(IMG_W, int(np.ceil(corners[:, 0].max())) + 2)
        v0 = max(0, int(np.floor(corners[:, 1].min())) - 2)
        v1 = min(IMG_H, int(np.ceil(corners[:, 1].max())) + 2)

        crop = im[v0:v1, u0:u1]
        bbox_px = crop.shape[0] * crop.shape[1]

        # Top 5 RGB clusters
        quant = (crop // 16) * 16 + 8
        flat = [tuple(c) for c in quant.reshape(-1, 3)]
        top5 = Counter(flat).most_common(5)

        # Inside detected pixels
        in_box = np.zeros((IMG_H, IMG_W), dtype=bool)
        in_box[v0:v1, u0:u1] = True
        mask = get_color_mask(im, pid)
        inside_px = int(np.sum(mask & in_box))
        inside_pass = inside_px >= 500

        print(f"[{pid}] {p['name_en']} ({p['color_hex']})")
        print(f"  - 2D BBox: u=[{u0}, {u1}], v=[{v0}, {v1}] (Total Area: {bbox_px:,} px)")
        print(f"  - Top 5 RGB Color Clusters inside BBox:")
        for (cr, cg, cb), cnt in top5:
            pct = cnt / bbox_px * 100
            print(f"      RGB=({cr:3d}, {cg:3d}, {cb:3d}): {cnt:5d} px ({pct:5.1f}%)")
        print(f"  - Inside Detected Pixels: {inside_px:,} px [{'PASS (>= 500 px)' if inside_pass else 'FAIL (< 500 px)'}]\n")

        summary_rows.append({
            "id": pid,
            "name": p["name_en"],
            "color_hex": p["color_hex"],
            "bbox_2d": f"u=[{u0},{u1}], v=[{v0},{v1}]",
            "bbox_area": bbox_px,
            "top_cluster": f"RGB=({top5[0][0][0]},{top5[0][0][1]},{top5[0][0][2]})",
            "inside_pixels": inside_px,
            "pass": inside_pass
        })

    print("------------------------------------------------------------------")
    print("| Part ID | Name | 2D BBox | Area (px) | Inside Detected | Verdict (>=500px) |")
    print("|---|---|---|---|---|---|")
    for r in summary_rows:
        verdict = "PASS" if r["pass"] else "미달"
        print(f"| `{r['id']}` | {r['name']} | `{r['bbox_2d']}` | {r['bbox_area']:,} | `{r['inside_pixels']:,}` px | **{verdict}** |")
    print("==================================================================")


if __name__ == "__main__":
    main()

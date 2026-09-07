#!/usr/bin/env python3
"""
scripts/measure_glow_diff.py

EXE-260906-P3-02-T4B-R4 Task 3: Difference Mask Tint Bleed Measurement
Quantifies tint bleed / glow outside the 2D projected bounding box for all 6 dynamic parts
using deterministic pixel difference between ON and OFF captures (|ON - OFF| >= 24).
"""

import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
MANIFEST_FILE = RAW_DIR / "t5_500k_partition_metrics.json"

IMG_W = 1280
IMG_H = 720
FOV_DEG = 60.0
ASPECT = IMG_W / IMG_H
DIFF_THRESHOLD = 24


def project_pt(pt: np.ndarray, cam_pos: np.ndarray, cam_target: np.ndarray):
    forward = (cam_target - cam_pos) / np.linalg.norm(cam_target - cam_pos)
    up = np.array([0.0, 1.0, 0.0], dtype=np.float64)
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    tan_half_fov = np.tan(np.radians(FOV_DEG / 2.0))

    rel = pt - cam_pos
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


def get_projected_bbox_2d(p5: list, p95: list, cam_pos: np.ndarray, cam_target: np.ndarray, margin: float = 0.03):
    bmin = np.array(p5, dtype=np.float64) - margin
    bmax = np.array(p95, dtype=np.float64) + margin
    corners = []
    for x in [bmin[0], bmax[0]]:
        for y in [bmin[1], bmax[1]]:
            for z in [bmin[2], bmax[2]]:
                proj = project_pt(np.array([x, y, z]), cam_pos, cam_target)
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


def main():
    if not MANIFEST_FILE.exists():
        print(f"[ERROR] Manifest file not found: {MANIFEST_FILE}")
        return

    manifest = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
    parts_meta = manifest.get("parts", [])
    dynamic_parts = [p for p in parts_meta if p.get("type") == "dynamic" and p.get("enabled", True)]

    results_data = {
        "directive": "EXE-260906-P3-02-T5",
        "method": "Deterministic pixel difference between ON and OFF captures (|ON - OFF| >= 24)",
        "diff_threshold": DIFF_THRESHOLD,
        "parts": {}
    }

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5 Task 0: Difference Mask Tint Bleed Ledger",
        "==================================================================",
        f"Diff Condition: max(|R_on - R_off|, |G_on - G_off|, |B_on - B_off|) >= {DIFF_THRESHOLD}",
        "Spec Requirement: outside_ratio_pct < 15.0% across all 6 closeup views",
        "Coverage (inside_px / bbox_2d_area): Reported for auditor evaluation",
        "------------------------------------------------------------------",
        "| 부품 ID | 명칭 | ON SHA | OFF SHA | 총 틴트 픽셀 | 내부 픽셀 | 외부 픽셀 | 밖 비율 | 2D BBox 투영 면적 | 덮임(커버리지) | 판정 (<15.0%) |",
        "|---|---|---|---|---|---|---|---|---|---|---|"
    ]

    print("==================================================================")
    print("  EXE-260906-P3-02-T4B-R4 Task 3: Difference Mask Tint Bleed Ledger")
    print("==================================================================")
    print(f"Diff Threshold: max(|R_on - R_off|, |G_on - G_off|, |B_on - B_off|) >= {DIFF_THRESHOLD}")
    print("Spec Requirement: outside_ratio_pct < 15.0%")
    print("------------------------------------------------------------------")
    print("| 부품 ID | 명칭 | ON SHA | OFF SHA | 총 틴트 픽셀 | 내부 픽셀 | 외부 픽셀 | 밖 비율 | 2D BBox 투영 면적 | 덮임(커버리지) | 판정 (<15.0%) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")

    pass_count = 0

    for p in dynamic_parts:
        pid = p["id"]
        short_id = pid.replace("box_", "")
        on_path = CAPTURES_DIR / f"marble_run01_part_selected_{short_id}.png"
        off_path = CAPTURES_DIR / f"marble_run01_part_selected_{short_id}_off.png"

        if not on_path.exists() or not off_path.exists():
            print(f"[ERROR] Capture pair not found for {pid}: {on_path.name}, {off_path.name}")
            continue

        im_on = np.array(Image.open(on_path).convert("RGB"), dtype=np.int16)
        im_off = np.array(Image.open(off_path).convert("RGB"), dtype=np.int16)
        on_sha = hashlib.sha256(on_path.read_bytes()).hexdigest()
        off_sha = hashlib.sha256(off_path.read_bytes()).hexdigest()

        # Deterministic pixel difference
        diff = np.max(np.abs(im_on - im_off), axis=-1)
        tint_mask = diff >= DIFF_THRESHOLD
        total_tint_px = int(np.sum(tint_mask))

        # Camera pose for part
        c = p["centroid_m"]
        is_left = c[0] < 0
        cam_x = (c[0] + 1.07) if is_left else (c[0] - 1.07)
        cam_y = 1.20
        cam_z = c[2] + 1.80
        cam_pos = np.array([cam_x, cam_y, cam_z], dtype=np.float64)
        cam_target = np.array([c[0], c[1], c[2]], dtype=np.float64)

        p5 = p["bounding_box_p5_p95"]["min"]
        p95 = p["bounding_box_p5_p95"]["max"]
        margin = p.get("margin_m", 0.03)
        u0, u1, v0, v1 = get_projected_bbox_2d(p5, p95, cam_pos, cam_target, margin)
        bbox_2d_area = (u1 - u0) * (v1 - v0)

        inside_mask = np.zeros((IMG_H, IMG_W), dtype=bool)
        inside_mask[v0:v1, u0:u1] = True

        inside_px = int(np.sum(tint_mask & inside_mask))
        outside_px = total_tint_px - inside_px
        outside_ratio_pct = (outside_px / total_tint_px * 100.0) if total_tint_px > 0 else 0.0
        coverage_pct = (inside_px / bbox_2d_area * 100.0) if bbox_2d_area > 0 else 0.0

        is_pass = (outside_ratio_pct < 15.0)
        if is_pass:
            pass_count += 1
        verdict = "PASS" if is_pass else f"미달 ({outside_ratio_pct:.1f}%)"

        row = (
            f"| `{pid}` | {p['name_en']} | {on_sha[:8]} | {off_sha[:8]} | "
            f"{total_tint_px:,} | {inside_px:,} | {outside_px:,} | "
            f"{outside_ratio_pct:.1f}% | {bbox_2d_area:,} px | {coverage_pct:.1f}% | **{verdict}** |"
        )
        print(row)
        txt_lines.append(row)

        results_data["parts"][pid] = {
            "name": p["name_en"],
            "on_capture": on_path.name,
            "on_sha256": on_sha,
            "off_capture": off_path.name,
            "off_sha256": off_sha,
            "total_tint_px": total_tint_px,
            "inside_px": inside_px,
            "outside_px": outside_px,
            "outside_ratio_pct": round(outside_ratio_pct, 2),
            "bbox_2d": [u0, u1, v0, v1],
            "bbox_2d_area": bbox_2d_area,
            "coverage_pct": round(coverage_pct, 2),
            "pass": is_pass
        }

    txt_lines.append("------------------------------------------------------------------")
    txt_lines.append(f"Summary: {pass_count}/{len(dynamic_parts)} parts passed (<15.0% outside ratio)")
    txt_lines.append("==================================================================")
    print("------------------------------------------------------------------")
    print(f"Summary: {pass_count}/{len(dynamic_parts)} parts passed (<15.0% outside ratio)")
    print("==================================================================")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_json = RAW_DIR / "t5_diff_glow.json"
    out_txt = RAW_DIR / "t5_diff_glow.txt"

    out_json.write_text(json.dumps(results_data, indent=2, ensure_ascii=False), encoding="utf-8")
    out_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    print(f"[+] Saved diff glow ledger -> {out_json} and {out_txt}")


if __name__ == "__main__":
    main()

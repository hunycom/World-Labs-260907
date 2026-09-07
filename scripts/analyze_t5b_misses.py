#!/usr/bin/env python3
"""
scripts/analyze_t5b_misses.py

EXE-260906-P3-02-T5-c Task 2: Failure Analysis of T5-b Dynamic Clicks (59 Misses)
Classifies 59 failed dynamic clicks into:
(i) Occlusion before bbox entry (bbox 진입 전 정적 히트)
(ii) Penetration after bbox entry (bbox 통과 후 정적 히트)
(iii) Zero-hit (무히트)
Calculates nearby splat count (radius 5 cm) for penetration cases.
Saves to docs/p3/raw/t5c_miss_analysis.txt and docs/p3/raw/t5c_miss_analysis.json.
"""

import json
import gzip
from pathlib import Path
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
EVAL_FILE = ROOT_DIR / "docs" / "p3" / "raw" / "t5b_pick_eval.json"
METRICS_FILE = ROOT_DIR / "docs" / "p3" / "raw" / "t4b_500k_partition_metrics.json"
SPZ_FILE = ROOT_DIR / "assets" / "p3" / "marble" / "run01_500k.spz"
L1_IND_FILE = ROOT_DIR / "assets" / "p3" / "marble" / "run01_parts" / "spz500k" / "part_0_box_l1_indices.bin"
R1_IND_FILE = ROOT_DIR / "assets" / "p3" / "marble" / "run01_parts" / "spz500k" / "part_1_box_r1_indices.bin"

OUT_TXT = ROOT_DIR / "docs" / "p3" / "raw" / "t5c_miss_analysis.txt"
OUT_JSON = ROOT_DIR / "docs" / "p3" / "raw" / "t5c_miss_analysis.json"


def main():
    eval_data = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))

    parts_bbox = {}
    for p in metrics["parts"]:
        parts_bbox[p["id"]] = {
            "min": np.array(p["bounding_box_p5_p95"]["min"]),
            "max": np.array(p["bounding_box_p5_p95"]["max"]),
            "centroid": np.array(p["centroid_m"])
        }

    # Load SPZ splats
    with open(SPZ_FILE, "rb") as f:
        raw = gzip.decompress(f.read())
    offset = 16
    N = 500000
    fixed = float(1 << 12)
    center_bytes = raw[offset:offset + N*9]
    raw_u8 = np.frombuffer(center_bytes, dtype=np.uint8).reshape((N, 3, 3))
    raw_u32 = (raw_u8[:, :, 0].astype(np.int32)) | (raw_u8[:, :, 1].astype(np.int32) << 8) | (raw_u8[:, :, 2].astype(np.int32) << 16)
    sign_mask = (raw_u32 & 0x800000) != 0
    raw_u32[sign_mask] -= 0x1000000
    xyz = raw_u32.astype(np.float32) / fixed

    s = 2.121173
    h = 1.2561374
    X = s * xyz[:, 0]
    Y = -s * xyz[:, 1] + h
    Z = -s * xyz[:, 2]
    splats_world = np.stack([X, Y, Z], axis=1)

    l1_indices = np.fromfile(L1_IND_FILE, dtype=np.int32)
    r1_indices = np.fromfile(R1_IND_FILE, dtype=np.int32)
    part_splats = {
        "box_l1": splats_world[l1_indices],
        "box_r1": splats_world[r1_indices]
    }

    views_cam = {
        "V1": {"eye": np.array([0.0, 1.6, 0.8]), "target": np.array([0.0, 1.3, -6.0])},
        "V2": {"eye": np.array([-0.6, 1.4, 0.3]), "target": parts_bbox["box_l1"]["centroid"]},
        "V3": {"eye": np.array([0.6, 1.4, 0.3]), "target": parts_bbox["box_r1"]["centroid"]}
    }
    aspect = 1093.0 / 701.0
    h_tan = np.tan(np.radians(60.0) / 2.0)
    w_tan = h_tan * aspect

    def get_ray(view, screen_coord):
        v = views_cam[view]
        f = (v["target"] - v["eye"]) / np.linalg.norm(v["target"] - v["eye"])
        r = np.cross(f, np.array([0.0, 1.0, 0.0]))
        r = r / np.linalg.norm(r)
        u = np.cross(r, f)
        ndc_x = (screen_coord[0] / 1280.0) * 2.0 - 1.0
        ndc_y = -(screen_coord[1] / 720.0) * 2.0 + 1.0
        d = ndc_x * w_tan * r + ndc_y * h_tan * u + f
        return v["eye"], d / np.linalg.norm(d)

    def ray_box_intersect(origin, direction, bmin, bmax, margin=0.03):
        bmin = bmin - margin
        bmax = bmax + margin
        t_min = -1e9
        t_max = 1e9
        for i in range(3):
            if abs(direction[i]) < 1e-8:
                if origin[i] < bmin[i] or origin[i] > bmax[i]:
                    return None, None
            else:
                t1 = (bmin[i] - origin[i]) / direction[i]
                t2 = (bmax[i] - origin[i]) / direction[i]
                if t1 > t2:
                    t1, t2 = t2, t1
                t_min = max(t_min, t1)
                t_max = min(t_max, t2)
                if t_min > t_max:
                    return None, None
        if t_max < 0:
            return None, None
        return max(0.0, t_min), t_max

    def count_splats_near_ray(origin, direction, splats, radius=0.05):
        v = splats - origin
        proj = np.dot(v, direction)
        valid = proj > 0
        v = v[valid]
        proj = proj[valid]
        perp_dist_sq = np.sum(v**2, axis=1) - proj**2
        return int(np.sum(perp_dist_sq <= radius**2))

    dyn_fails = [r for r in eval_data["eval_results"] if r["target_type"] == "dynamic" and not r["success"]]
    assert len(dyn_fails) == 59, f"Expected 59 failures, got {len(dyn_fails)}"

    analysis_rows = []
    cat_counts = {"occlusion": 0, "penetration": 0, "zero_hit": 0}

    for idx, item in enumerate(dyn_fails, start=1):
        view = item["view"]
        coord = item["screen_coord"]
        exp_part = item["expected_part_id"]
        hit_dist = item["hit_distance"]
        hit_part = item["hit_part_id"]
        hits_cnt = item["hits_count"]

        if hits_cnt == 0:
            cat = "zero_hit"
            cat_name = "무히트"
            t_entry = None
            t_entry_str = "-"
            splats_5cm = 0
            dist_diff = None
        else:
            origin, direction = get_ray(view, coord)
            bmin = parts_bbox[exp_part]["min"]
            bmax = parts_bbox[exp_part]["max"]
            t_ent, t_ext = ray_box_intersect(origin, direction, bmin, bmax, margin=0.03)

            if t_ent is None:
                cat = "occlusion"
                cat_name = "폐색(BBox외곽)"
                t_entry = None
                t_entry_str = "Miss"
                splats_5cm = 0
                dist_diff = None
            elif hit_dist < t_ent - 0.01:
                cat = "occlusion"
                cat_name = "폐색(전방장애)"
                t_entry = float(t_ent)
                t_entry_str = f"{t_ent:.4f} m"
                splats_5cm = 0
                dist_diff = float(hit_dist - t_ent)
            else:
                cat = "penetration"
                cat_name = "관통(BBox내부/후방)"
                t_entry = float(t_ent)
                t_entry_str = f"{t_ent:.4f} m"
                splats_5cm = count_splats_near_ray(origin, direction, part_splats[exp_part], radius=0.05)
                dist_diff = float(hit_dist - t_ent)

        cat_counts[cat] += 1
        analysis_rows.append({
            "num": idx,
            "sample_index": item["index"],
            "view": view,
            "expected_part_id": exp_part,
            "screen_coord": coord,
            "bbox_entry_m": t_entry,
            "hit_distance_m": hit_dist,
            "hit_part_id": hit_part,
            "hits_count": hits_cnt,
            "dist_diff_m": dist_diff,
            "category": cat,
            "category_name": cat_name,
            "splats_near_5cm": splats_5cm
        })

    total_classified = sum(cat_counts.values())
    assert total_classified == 59, f"Total classified {total_classified} != 59"

    lines = []
    lines.append("=========================================================================================================")
    lines.append("  EXE-260906-P3-02-T5-c Task 2: T5-b Dynamic Picking Miss Analysis Ledger (59 Misses)")
    lines.append("=========================================================================================================")
    lines.append(f"Total Dynamic Misses Analyzed: 59 / 150")
    lines.append(f"Classification Summary:")
    lines.append(f"  (i)   bbox 진입 전 정적 히트 (폐색): {cat_counts['occlusion']} 건")
    lines.append(f"  (ii)  bbox 통과 후 정적 히트 (관통): {cat_counts['penetration']} 건 (L1/R1 중공 구조 및 스플랫 틈새)")
    lines.append(f"  (iii) 무히트 (Zero-hit):             {cat_counts['zero_hit']} 건")
    lines.append(f"  합계:                                {total_classified} 건 (전수 분류 완료, 100%)")
    lines.append("---------------------------------------------------------------------------------------------------------")
    lines.append("No | Idx | View | Expected | Screen [X,Y] | BBox Entry | Hit Dist | Hit Part | Hits | Dist Diff | Near 5cm | Category")
    lines.append("---|-----|------|----------|--------------|------------|----------|----------|------|-----------|----------|---------")
    for r in analysis_rows:
        entry_s = f"{r['bbox_entry_m']:.4f}m" if r['bbox_entry_m'] is not None else "Miss    "
        diff_s = f"{r['dist_diff_m']:+.4f}m" if r['dist_diff_m'] is not None else "     -  "
        lines.append(
            f"{r['num']:2d} | {r['sample_index']:3d} | {r['view']:4s} | {r['expected_part_id']:8s} | "
            f"[{r['screen_coord'][0]:4d},{r['screen_coord'][1]:4d}] | {entry_s:10s} | "
            f"{r['hit_distance_m']:.4f}m | {r['hit_part_id']:8s} | {r['hits_count']:4d} | "
            f"{diff_s:9s} | {r['splats_near_5cm']:8d} | {r['category_name']}"
        )
    lines.append("=========================================================================================================")

    txt_content = "\n".join(lines) + "\n"
    OUT_TXT.write_text(txt_content, encoding="utf-8")

    json_out = {
        "directive": "EXE-260906-P3-02-T5-c",
        "total_failures": 59,
        "classification_counts": {
            "occlusion": cat_counts["occlusion"],
            "penetration": cat_counts["penetration"],
            "zero_hit": cat_counts["zero_hit"],
            "total": total_classified
        },
        "pass_criteria_sum_check": (total_classified == 59),
        "failures": analysis_rows
    }
    OUT_JSON.write_text(json.dumps(json_out, indent=2), encoding="utf-8")
    print(f"[+] Successfully generated {OUT_TXT} and {OUT_JSON}")
    print(f"[+] Total classified: {total_classified} / 59")


if __name__ == "__main__":
    main()

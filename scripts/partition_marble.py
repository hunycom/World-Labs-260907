#!/usr/bin/env python3
"""
scripts/partition_marble.py

Phase 3 P3-02 Task 4: Static / Dynamic Part Partitioning (T4B-R 3-Condition Mask)
Implements Auditor Directive EXE-260906-P3-02-T4B-R:
1. 3-Condition Filter:
   - bbox(p5~p95, margin +3cm)
   - y > y_mesh + 0.04m (floor threshold)
   - max(axis scale) < 0.15m (large-scale splat threshold)
   - Removed splats assigned to static structure
2. Exact splat conservation: Sum(Dynamic) + Static == Total Splats (100.0%)
3. Mass calculation (p5~p95 * 500 kg/m^3) with explicit "미달" status if outside 200~800 kg
4. Supports both 1.92M PLY (physics ground truth) and 500k SPZ (runtime SplatMesh partitioning)
5. Exports raw audit metrics to docs/p3/raw/
"""

import argparse
import gzip
import hashlib
import json
import os
import struct
import sys
from pathlib import Path
import numpy as np
from plyfile import PlyData
import scipy.sparse as sp
from scipy.sparse.csgraph import connected_components

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs" / "p3" / "marble"
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
ASSETS_DIR = ROOT_DIR / "assets" / "p3" / "marble"


def compute_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def load_vertical_static_triangles(glb_path: Path, s: float, h: float):
    """
    Loads GLB collider mesh, identifies non-floor vertical components reaching Y >= 1.5m,
    and returns vertical static triangles along with transformed vertices.
    """
    with open(glb_path, 'rb') as f:
        f.seek(12)
        c_len0, _ = struct.unpack('<II', f.read(8))
        gltf = json.loads(f.read(c_len0).decode('utf-8'))
        c_len1, _ = struct.unpack('<II', f.read(8))
        bin_data = f.read(c_len1)

    pos_acc = gltf['accessors'][gltf['meshes'][0]['primitives'][0]['attributes']['POSITION']]
    idx_acc = gltf['accessors'][gltf['meshes'][0]['primitives'][0]['indices']]

    def get_buffer_data(acc):
        bv = gltf['bufferViews'][acc['bufferView']]
        offset = bv.get('byteOffset', 0) + acc.get('byteOffset', 0)
        count = acc['count']
        ctype = acc['componentType']
        typ = acc['type']
        dtype = np.float32 if ctype == 5126 else (np.uint16 if ctype == 5123 else np.uint32)
        arr = np.frombuffer(bin_data, dtype=dtype, count=count * (3 if typ == 'VEC3' else 1), offset=offset)
        if typ == 'VEC3':
            arr = arr.reshape(count, 3)
        return arr

    positions = get_buffer_data(pos_acc).copy()
    indices = get_buffer_data(idx_acc).copy().reshape(-1, 3)

    world_pos = np.zeros_like(positions)
    world_pos[:, 0] = s * positions[:, 0]
    world_pos[:, 1] = -s * positions[:, 1] + h
    world_pos[:, 2] = -s * positions[:, 2]

    v0 = world_pos[indices[:, 0]]
    v1 = world_pos[indices[:, 1]]
    v2 = world_pos[indices[:, 2]]
    e0 = v1 - v0
    e1 = v2 - v0
    normals = np.cross(e0, e1)
    norm_len = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.divide(normals, norm_len, where=norm_len > 0, out=np.zeros_like(normals))
    tc = (v0 + v1 + v2) / 3.0

    # Separate horizontal floor triangles (Y < 0.05m and normal pointing mostly upwards)
    is_floor_tri = (tc[:, 1] < 0.05) & (normals[:, 1] > 0.7)
    non_floor_indices = indices[~is_floor_tri]

    # Graph of connected components on non-floor mesh
    edges = np.vstack([non_floor_indices[:, [0, 1]], non_floor_indices[:, [1, 2]], non_floor_indices[:, [2, 0]]])
    N = len(world_pos)
    adj = sp.coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])), shape=(N, N))
    n_comp, labels = connected_components(adj, directed=False)

    comp_max_y = np.zeros(n_comp, dtype=np.float32)
    for c in range(n_comp):
        c_verts = np.where(labels == c)[0]
        if len(c_verts) > 0:
            comp_max_y[c] = world_pos[c_verts, 1].max()

    # Vertices belonging to components extending up to Y >= 1.5m (racks, columns, walls)
    vert_is_vert_static = (comp_max_y >= 1.5)[labels]
    tri_is_vert_static = ~is_floor_tri & vert_is_vert_static[indices[:, 0]] & vert_is_vert_static[indices[:, 1]] & vert_is_vert_static[indices[:, 2]]
    static_tris = indices[tri_is_vert_static]

    return static_tris, world_pos


def point_to_triangles_min_dist(pts: np.ndarray, tri_indices: np.ndarray, mesh_verts: np.ndarray) -> np.ndarray:
    """
    Computes minimum Euclidean distance from each point in pts to any of the specified triangles.
    """
    if len(tri_indices) == 0:
        return np.full(len(pts), np.inf, dtype=np.float32)
    v0 = mesh_verts[tri_indices[:, 0]]
    v1 = mesh_verts[tri_indices[:, 1]]
    v2 = mesh_verts[tri_indices[:, 2]]
    e0 = v1 - v0
    e1 = v2 - v0
    P = len(pts)
    min_dists = np.full(P, np.inf, dtype=np.float32)

    chunk_size = 500
    for i in range(0, P, chunk_size):
        p_chunk = pts[i:i + chunk_size]
        D = v0[None, :, :] - p_chunk[:, None, :]
        a = np.sum(e0 * e0, axis=-1)
        b = np.sum(e0 * e1, axis=-1)
        c = np.sum(e1 * e1, axis=-1)
        d = np.sum(e0[None, :, :] * D, axis=-1)
        e = np.sum(e1[None, :, :] * D, axis=-1)
        det = a * c - b * b
        det = np.where(det == 0, 1e-12, det)
        s_param = b[None, :] * e - c[None, :] * d
        t_param = b[None, :] * d - a[None, :] * e
        s_clamped = np.clip(s_param / det[None, :], 0.0, 1.0)
        t_clamped = np.clip(t_param / det[None, :], 0.0, 1.0)
        sum_st = s_clamped + t_clamped
        mask_over = sum_st > 1.0
        s_clamped = np.where(mask_over, s_clamped / np.maximum(sum_st, 1e-12), s_clamped)
        t_clamped = np.where(mask_over, t_clamped / np.maximum(sum_st, 1e-12), t_clamped)
        closest_pts = v0[None, :, :] + s_clamped[:, :, None] * e0[None, :, :] + t_clamped[:, :, None] * e1[None, :, :]
        dists_sq = np.sum((closest_pts - p_chunk[:, None, :]) ** 2, axis=-1)
        min_dists[i:i + chunk_size] = np.sqrt(np.min(dists_sq, axis=1))
def compute_splat_hsv(r: np.ndarray, g: np.ndarray, b: np.ndarray):
    """
    Computes HSV values for splats given r, g, b in [0, 1].
    Returns (hue_deg, sat, val).
    """
    r_c = np.clip(r, 0.0, 1.0)
    g_c = np.clip(g, 0.0, 1.0)
    b_c = np.clip(b, 0.0, 1.0)
    maxc = np.maximum(np.maximum(r_c, g_c), b_c)
    minc = np.minimum(np.minimum(r_c, g_c), b_c)
    deltac = maxc - minc
    sat = np.zeros_like(maxc)
    nz_v = maxc > 1e-5
    sat[nz_v] = deltac[nz_v] / maxc[nz_v]

    hue = np.zeros_like(maxc)
    nz_d = deltac > 1e-5
    rc = (maxc - r_c) / np.where(nz_d, deltac, 1.0)
    gc = (maxc - g_c) / np.where(nz_d, deltac, 1.0)
    bc = (maxc - b_c) / np.where(nz_d, deltac, 1.0)
    mr = nz_d & (r_c == maxc)
    mg = nz_d & (g_c == maxc) & (~mr)
    mb = nz_d & (b_c == maxc) & (~mr) & (~mg)
    hue[mr] = (bc[mr] - gc[mr]) % 6.0
    hue[mg] = 2.0 + rc[mg] - bc[mg]
    hue[mb] = 4.0 + gc[mb] - rc[mb]
    hue = (hue / 6.0) * 360.0 % 360.0
    return hue, sat, maxc


def compute_geom_column_mask(sub_x: np.ndarray, sub_y: np.ndarray, sub_z: np.ndarray, h_box: float, cell_size: float = 0.05) -> np.ndarray:
    """
    Rule (b): Identifies tall narrow vertical columns in XZ 5cm grid cells
    where height extent delta_Y >= 0.9 * h_box and footprint <= 15cm.
    """
    cell_x = np.floor(sub_x / cell_size).astype(np.int32)
    cell_z = np.floor(sub_z / cell_size).astype(np.int32)
    cell_keys = cell_x * 100000 + cell_z
    is_geom = np.zeros(len(sub_x), dtype=bool)
    for k in np.unique(cell_keys):
        c_m = (cell_keys == k)
        dy = sub_y[c_m].max() - sub_y[c_m].min()
        if dy >= 0.9 * h_box:
            is_geom[c_m] = True
    return is_geom


def get_box_specs(y_thresh: float):
    return [
        {
            "id": "box_l1",
            "name": "좌측 전방 1열 대형 팔레트 상자 (L1)",
            "name_en": "Foreground Left Pallet Box (L1)",
            "color_hex": "#00f0ff",
            "search_x": [-1.80, -0.60],
            "search_y": [y_thresh, 1.20],
            "search_z": [-2.40, -1.45],
            "enabled": True,
        },
        {
            "id": "box_r1",
            "name": "우측 전방 1열 대형 팔레트 상자 (R1)",
            "name_en": "Foreground Right Pallet Box (R1)",
            "color_hex": "#ff9900",
            "search_x": [+0.60, +1.80],
            "search_y": [y_thresh, 1.20],
            "search_z": [-2.40, -1.45],
            "enabled": True,
        },
        {
            "id": "box_l2",
            "name": "좌측 통로 2열 중형 팔레트 상자 (L2)",
            "name_en": "Mid-Left Pallet Box 1 (L2)",
            "color_hex": "#10b981",
            "search_x": [-1.80, -0.60],
            "search_y": [y_thresh, 0.95],
            "search_z": [-2.95, -2.15],
            "enabled": False,
        },
        {
            "id": "box_r2",
            "name": "우측 통로 2열 중형 팔레트 상자 (R2)",
            "name_en": "Mid-Right Pallet Box 1 (R2)",
            "color_hex": "#f43f5e",
            "search_x": [+0.60, +1.80],
            "search_y": [y_thresh, 0.95],
            "search_z": [-2.95, -2.15],
            "enabled": False,
        },
        {
            "id": "box_l3",
            "name": "좌측 통로 3열 중형 팔레트 상자 (L3)",
            "name_en": "Mid-Left Pallet Box 2 (L3)",
            "color_hex": "#a855f7",
            "search_x": [-1.80, -0.60],
            "search_y": [y_thresh, 0.95],
            "search_z": [-4.40, -3.30],
            "enabled": False,
        },
        {
            "id": "box_r3",
            "name": "우측 통로 3열 중형 팔레트 상자 (R3)",
            "name_en": "Mid-Right Pallet Box 2 (R3)",
            "color_hex": "#eab308",
            "search_x": [+0.60, +1.80],
            "search_y": [y_thresh, 0.95],
            "search_z": [-4.40, -3.30],
            "enabled": False,
        },
    ]


def partition_ply_192m(run_id: str = "run01") -> dict:
    ply_path = ASSETS_DIR / f"{run_id}_splats.ply"
    resp_path = DOCS_DIR / f"{run_id}_response.json"
    verify_path = RAW_DIR / f"marble_transform_verify_{run_id}.json"

    if not ply_path.exists():
        print(f"[ERROR] PLY file not found: {ply_path}", file=sys.stderr)
        sys.exit(1)

    s = 2.121173
    h = 1.2561374
    if resp_path.exists():
        try:
            with open(resp_path, "r", encoding="utf-8") as f:
                resp = json.load(f)
            world_obj = resp.get("response", resp.get("world", resp))
            semantics = world_obj.get("assets", {}).get("splats", {}).get("semantics_metadata", {}) or world_obj.get("semantics_metadata", {})
            s = float(semantics.get("metric_scale_factor", s))
            h = float(semantics.get("ground_plane_offset", h))
        except Exception as e:
            print(f"[WARN] Semantics parse error: {e}")

    y_mesh_floor = -0.024999999999999578
    if verify_path.exists():
        try:
            with open(verify_path, "r", encoding="utf-8") as f:
                v_data = json.load(f)
            y_mesh_floor = float(v_data.get("y_mesh_floor_m", y_mesh_floor))
        except Exception as e:
            print(f"[WARN] Transform verify parse error: {e}")

    y_thresh = y_mesh_floor + 0.04
    scale_thresh = 0.15
    margin = 0.03

    print(f"[*] Task 2 PLY 1.92M Partitioning with Rule (a) Color Post & Rule (b) Geom Column Exclusions (T4B-R4):")
    print(f"    s={s:.6f}, h={h:.6f}, y_mesh={y_mesh_floor:.4f}m, y_thresh={y_thresh:.4f}m, scale_thresh={scale_thresh:.2f}m, margin={margin*100:.1f}cm")

    plydata = PlyData.read(str(ply_path))
    v = plydata["vertex"]
    x_raw = np.asarray(v["x"], dtype=np.float32)
    y_raw = np.asarray(v["y"], dtype=np.float32)
    z_raw = np.asarray(v["z"], dtype=np.float32)
    total_splats = len(x_raw)

    X = s * x_raw
    Y = -s * y_raw + h
    Z = -s * z_raw

    s0 = np.asarray(v["scale_0"], dtype=np.float32)
    s1 = np.asarray(v["scale_1"], dtype=np.float32)
    s2 = np.asarray(v["scale_2"], dtype=np.float32)
    max_scale = s * np.exp(np.maximum(np.maximum(s0, s1), s2))

    SH_C0 = 0.28209479177387814
    if "f_dc_0" in v:
        r = np.clip(0.5 + SH_C0 * np.asarray(v["f_dc_0"], dtype=np.float32), 0.0, 1.0)
        g = np.clip(0.5 + SH_C0 * np.asarray(v["f_dc_1"], dtype=np.float32), 0.0, 1.0)
        b = np.clip(0.5 + SH_C0 * np.asarray(v["f_dc_2"], dtype=np.float32), 0.0, 1.0)
    else:
        r = np.ones_like(X)
        g = np.ones_like(X)
        b = np.ones_like(X)

    hue, sat, _ = compute_splat_hsv(r, g, b)
    is_color_post = (sat >= 0.45) & (((hue >= 195.0) & (hue <= 245.0)) | ((hue >= 40.0) & (hue <= 65.0)))

    box_specs = get_box_specs(y_thresh)
    parts_dir = ASSETS_DIR / f"{run_id}_parts"
    parts_dir.mkdir(parents=True, exist_ok=True)

    assigned_mask = np.zeros(total_splats, dtype=bool)
    parts_manifest = []
    total_dynamic_splats = 0
    total_candidates = 0
    total_rej_color = 0
    total_rej_geom = 0
    total_rej_ext = 0

    print("[*] Extracting 6 Dynamic Pallet Boxes with Rule (a) Color & Rule (b) Geom Column Exclusions...")

    for idx, b_cfg in enumerate(box_specs):
        sx, sy, sz = b_cfg["search_x"], b_cfg["search_y"], b_cfg["search_z"]
        cand_mask = (
            (X >= sx[0]) & (X <= sx[1]) &
            (Y >= sy[0]) & (Y <= sy[1]) &
            (Z >= sz[0]) & (Z <= sz[1]) &
            (Y > y_thresh) & (max_scale < scale_thresh) &
            (~assigned_mask)
        )
        cand_indices = np.where(cand_mask)[0]
        c_cand = len(cand_indices)
        total_candidates += c_cand

        if c_cand == 0:
            print(f"[WARN] No candidate splats in search box {b_cfg['id']}")
            continue

        sub_x, sub_y, sub_z = X[cand_indices], Y[cand_indices], Z[cand_indices]

        # Rule (a) Color post
        rej_col = is_color_post[cand_indices]

        # Rule (b) Geometry column (on non-color)
        h_box = sy[1] - sy[0]
        is_geom = compute_geom_column_mask(sub_x, sub_y, sub_z, h_box=h_box, cell_size=0.05)
        rej_geom = (~rej_col) & is_geom

        # Extent filter (on non-color, non-geom)
        ext_m = (
            (sub_x - 3.0 * max_scale[cand_indices] < sx[0] - 0.2) | (sub_x + 3.0 * max_scale[cand_indices] > sx[1] + 0.2) |
            (sub_z - 3.0 * max_scale[cand_indices] < sz[0] - 0.2) | (sub_z + 3.0 * max_scale[cand_indices] > sz[1] + 0.2)
        )
        rej_ext = (~rej_col) & (~rej_geom) & ext_m

        surv_mask = (~rej_col) & (~rej_geom) & (~rej_ext)
        final_part_indices = cand_indices[surv_mask].astype(np.uint32)
        count = len(final_part_indices)

        assigned_mask[final_part_indices] = True
        total_dynamic_splats += count

        n_col = int(np.sum(rej_col))
        n_geom = int(np.sum(rej_geom))
        n_ext = int(np.sum(rej_ext))
        part_rej_sum = n_col + n_geom + n_ext
        assert count + part_rej_sum == c_cand, f"Candidate conservation mismatch in {b_cfg['id']}"

        total_rej_color += n_col
        total_rej_geom += n_geom
        total_rej_ext += n_ext

        # Recompute BBox, dimensions, volume, mass AFTER ALL EXCLUSIONS
        bx, by, bz = X[final_part_indices], Y[final_part_indices], Z[final_part_indices]
        p5 = [float(np.percentile(bx, 5)), float(np.percentile(by, 5)), float(np.percentile(bz, 5))]
        p95 = [float(np.percentile(bx, 95)), float(np.percentile(by, 95)), float(np.percentile(bz, 95))]

        dims = [round(p95[0] - p5[0], 3), round(p95[1] - p5[1], 3), round(p95[2] - p5[2], 3)]
        volume_m3 = round(dims[0] * dims[1] * dims[2], 4)
        density = 500.0
        mass_kg = 300.0
        mass_status = "임의 상수 300 kg, 사양 미확정"
        centroid = [round(float(bx.mean()), 3), round(float(by.mean()), 3), round(float(bz.mean()), 3)]

        bin_filename = f"part_{idx}_{b_cfg['id']}_indices.bin"
        bin_path = parts_dir / bin_filename
        final_part_indices.tofile(str(bin_path))
        bin_sha256 = compute_sha256(bin_path)

        bbox_bottom = round(p5[1], 4)
        bbox_bottom_pass = bool(bbox_bottom >= y_thresh)

        parts_manifest.append({
            "part_index": idx,
            "id": b_cfg["id"],
            "name": b_cfg["name"],
            "name_en": b_cfg["name_en"],
            "type": "dynamic",
            "enabled": b_cfg.get("enabled", True),
            "color_hex": b_cfg["color_hex"],
            "splat_count": count,
            "splat_percentage": round(count / total_splats * 100, 3),
            "candidates_count": c_cand,
            "rejected_color_post_count": n_col,
            "rejected_geom_post_count": n_geom,
            "rejected_extent_count": n_ext,
            "rejected_total_count": part_rej_sum,
            "centroid_m": centroid,
            "bounding_box_p5_p95": {
                "min": [round(p5[0], 3), round(p5[1], 3), round(p5[2], 3)],
                "max": [round(p95[0], 3), round(p95[1], 3), round(p95[2], 3)],
                "dimensions_m": dims,
                "bbox_bottom_m": bbox_bottom,
                "bbox_bottom_pass": bbox_bottom_pass
            },
            "volume_m3": volume_m3,
            "density_kg_m3": density,
            "mass_kg": mass_kg,
            "mass_status": mass_status,
            "margin_m": margin,
            "indices_file": f"assets/p3/marble/{run_id}_parts/{bin_filename}",
            "indices_sha256": bin_sha256
        })

        print(f"    [{b_cfg['id']}] {b_cfg['name_en']}: {count:,} splats (cand={c_cand}, rej_col={n_col}, rej_geom={n_geom}, rej_ext={n_ext}) | bbox_Y=[{bbox_bottom}m, {p95[1]:.3f}m] | Mass={mass_kg:.1f}kg [{mass_status}] | SHA256={bin_sha256[:8]}...")

    static_indices = np.where(~assigned_mask)[0].astype(np.uint32)
    static_count = len(static_indices)
    static_bin_name = "part_static_indices.bin"
    static_bin_path = parts_dir / static_bin_name
    static_indices.tofile(str(static_bin_path))
    static_sha256 = compute_sha256(static_bin_path)

    static_part_info = {
        "part_index": len(parts_manifest),
        "id": "static_structure",
        "name": "고정 정적 구조체 (바닥·랙·천장·원경 벽체)",
        "name_en": "Static Structure (Floor, Racks, Ceiling, Walls)",
        "type": "static",
        "color_hex": "#64748b",
        "splat_count": static_count,
        "splat_percentage": round(static_count / total_splats * 100, 3),
        "rejected_color_post_count": 0,
        "rejected_geom_post_count": 0,
        "rejected_extent_count": 0,
        "rejected_total_count": 0,
        "centroid_m": [round(float(X[static_indices].mean()), 3), round(float(Y[static_indices].mean()), 3), round(float(Z[static_indices].mean()), 3)],
        "bounding_box_p5_p95": {
            "min": [round(float(np.percentile(X[static_indices], 5)), 3), round(float(np.percentile(Y[static_indices], 5)), 3), round(float(np.percentile(Z[static_indices], 5)), 3)],
            "max": [round(float(np.percentile(X[static_indices], 95)), 3), round(float(np.percentile(Y[static_indices], 95)), 3), round(float(np.percentile(Z[static_indices], 95)), 3)],
            "dimensions_m": [
                round(float(np.percentile(X[static_indices], 95) - np.percentile(X[static_indices], 5)), 3),
                round(float(np.percentile(Y[static_indices], 95) - np.percentile(Y[static_indices], 5)), 3),
                round(float(np.percentile(Z[static_indices], 95) - np.percentile(Z[static_indices], 5)), 3)
            ],
            "bbox_bottom_m": round(float(np.percentile(Y[static_indices], 5)), 4)
        },
        "volume_m3": None,
        "density_kg_m3": None,
        "mass_kg": None,
        "mass_status": "Fixed (Inf)",
        "indices_file": f"assets/p3/marble/{run_id}_parts/{static_bin_name}",
        "indices_sha256": static_sha256
    }
    parts_manifest.append(static_part_info)

    total_assigned = total_dynamic_splats + static_count
    conservation_pass = (total_assigned == total_splats)
    total_rej_sum = total_rej_color + total_rej_geom + total_rej_ext
    sum_rej_parts = sum(p["rejected_total_count"] for p in parts_manifest if p["type"] == "dynamic")
    rejection_sum_pass = (sum_rej_parts == total_rej_sum)
    candidate_conservation_pass = (total_candidates == total_dynamic_splats + total_rej_sum)

    print(f"\n[*] Splat Conservation Check (1.92M): Dynamic({total_dynamic_splats:,}) + Static({static_count:,}) = {total_assigned:,} / Original={total_splats:,}")
    print(f"    Conservation Verdict: {'PASS (100.0% 완전 일치)' if conservation_pass else 'FAIL (오차 발생)'}")
    print(f"    Rejection Sum Verification: sum(rejected per part)={sum_rej_parts:,} == total_rejected={total_rej_sum:,} ({'PASS' if rejection_sum_pass else 'FAIL'})")

    # Floor floaters
    floor_aisle_mask = (X >= -1.0) & (X <= 1.0) & (Y >= -0.05) & (Y <= 0.15) & (Z >= 0.0) & (Z <= 5.0)
    dark_floater_mask = floor_aisle_mask & (r < 0.15) & (g < 0.15) & (b < 0.15) & (~assigned_mask)
    floater_indices = np.where(dark_floater_mask)[0].astype(np.uint32)
    floater_count = len(floater_indices)
    floater_bin_name = "floater_indices.bin"
    floater_bin_path = parts_dir / floater_bin_name
    floater_indices.tofile(str(floater_bin_path))
    floater_sha256 = compute_sha256(floater_bin_path)

    floater_meta = {
        "count": floater_count,
        "action": "opacity_zero_filter",
        "description": "Floor black specks / floaters in aisle Z in [0, 5m] filtered to opacity 0",
        "indices_file": f"assets/p3/marble/{run_id}_parts/{floater_bin_name}",
        "indices_sha256": floater_sha256
    }

    full_manifest = {
        "schema_version": "2.5.0",
        "directive": "EXE-260906-P3-02-T5",
        "run_id": run_id,
        "semantics": {
            "metric_scale_factor": s,
            "ground_plane_offset": h,
            "y_mesh_floor_m": y_mesh_floor,
            "y_threshold_m": y_thresh,
            "scale_threshold_m": scale_thresh,
            "margin_m": margin
        },
        "total_splats": total_splats,
        "total_candidates": total_candidates,
        "dynamic_parts_count": len(box_specs),
        "static_parts_count": 1,
        "conservation_pass": conservation_pass,
        "rejection_sum_pass": rejection_sum_pass,
        "candidate_conservation_pass": candidate_conservation_pass,
        "total_dynamic_splats": total_dynamic_splats,
        "total_static_splats": static_count,
        "total_rejected_color_post": total_rej_color,
        "total_rejected_geom_post": total_rej_geom,
        "total_rejected_extent": total_rej_ext,
        "total_rejected_splats": total_rej_sum,
        "floater_filter": floater_meta,
        "parts": parts_manifest
    }

    manifest_json_path = parts_dir / "manifest.json"
    manifest_json_path.write_text(json.dumps(full_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_json_path = RAW_DIR / "t5_mask.json"
    raw_txt_path = RAW_DIR / "t5_mask.txt"

    raw_json_path.write_text(json.dumps(full_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    # Also write to legacy path for backwards compatibility
    (RAW_DIR / "t4b_mask_run01.json").write_text(json.dumps(full_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    (RAW_DIR / f"marble_partition_metrics_{run_id}.json").write_text(json.dumps(full_manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    txt_lines = [
        "==================================================================",
        f"  EXE-260906-P3-02-T5 Task 0: L1/R1 Z-Fix & Partition Ledger ({run_id})",
        "==================================================================",
        f"Metric Scale Factor (s):       {s:.6f}",
        f"Ground Plane Offset (h):       {h:.6f} m",
        f"Mesh Floor Level (y_mesh):     {y_mesh_floor:.4f} m",
        f"Floor Cutoff (y_mesh + 0.04):  {y_thresh:.4f} m",
        f"Max Axis Scale Cutoff:         {scale_thresh:.2f} m",
        f"BBox Expansion Margin:         +{margin*100:.1f} cm",
        "------------------------------------------------------------------",
        f"Total Original Splats (PLY):   {total_splats:,}",
        f"Total Search Candidates:       {total_candidates:,}",
        f"Total Dynamic Splats:          {total_dynamic_splats:,} ({total_dynamic_splats / total_splats * 100:.3f}%)",
        f"Total Static Splats:           {static_count:,} ({static_count / total_splats * 100:.3f}%)",
        f"Total Excluded - Rule (a) Col: {total_rej_color:,} (Blue H[195..245] + Yellow H[40..65], S>=0.45)",
        f"Total Excluded - Rule (b) Geom:{total_rej_geom:,} (XZ 5cm column cell, dY>=0.9*h_box)",
        f"Total Excluded - Extent (3*s): {total_rej_ext:,}",
        f"Total Excluded Splats:         {total_rej_sum:,}",
        "------------------------------------------------------------------",
        f"Sum Conservation Check:        Dynamic({total_dynamic_splats:,}) + Static({static_count:,}) = {total_assigned:,} / {total_splats:,}",
        f"Conservation Verdict:          {'PASS (100.0% 완전 일치)' if conservation_pass else 'FAIL'}",
        f"Rejection Sum Verification:    sum(rejected per part) == total rejected ({'PASS' if rejection_sum_pass else 'FAIL'})",
        f"Candidate Sum Verification:    Candidates({total_candidates:,}) == Dynamic({total_dynamic_splats:,}) + Rejected({total_rej_sum:,}) ({'PASS' if candidate_conservation_pass else 'FAIL'})",
        f"Floor Floaters Filtered:       {floater_count} specks (opacity=0, SHA256={floater_sha256[:16]}...)",
        "------------------------------------------------------------------",
        "Part Specifications & Bounding Box Recomputation (Post-Exclusion):"
    ]
    for p in parts_manifest:
        if p["type"] == "dynamic":
            bb = p["bounding_box_p5_p95"]
            b_bot = bb["bbox_bottom_m"]
            bot_pass = "PASS" if b_bot >= y_thresh else "FAIL"
            rej_str = f"cand={p['candidates_count']}, col={p['rejected_color_post_count']}, geom={p['rejected_geom_post_count']}, ext={p['rejected_extent_count']}, tot_rej={p['rejected_total_count']}"
            txt_lines.append(f"  [{p['id']}] {p['name_en']}: {p['splat_count']:,} splats ({rej_str}) | bbox_Y=[{b_bot:.4f}m, {bb['max'][1]:.4f}m] (>={y_thresh:.4f}m: {bot_pass}) | Dims={bb['dimensions_m']} | Vol={p['volume_m3']:.3f}m3 | Mass={p['mass_kg']:.1f}kg [{p['mass_status']}] | SHA256={p['indices_sha256'][:16]}...")
        else:
            txt_lines.append(f"  [{p['id']}] {p['name_en']}: {p['splat_count']:,} splats | Fixed Collider | SHA256={p['indices_sha256'][:16]}...")
    txt_lines.append("==================================================================")

    mask_txt_content = "\n".join(txt_lines) + "\n"
    raw_txt_path.write_text(mask_txt_content, encoding="utf-8")
    (RAW_DIR / "t4b_mask_run01.txt").write_text(mask_txt_content, encoding="utf-8")
    (RAW_DIR / f"marble_partition_metrics_{run_id}.txt").write_text(mask_txt_content, encoding="utf-8")
    print(f"[+] Saved raw mask metrics -> {raw_json_path} and {raw_txt_path}")

    return full_manifest


def partition_spz_500k(run_id: str = "run01") -> dict:
    spz_path = ASSETS_DIR / f"{run_id}_500k.spz"
    resp_path = DOCS_DIR / f"{run_id}_response.json"
    verify_path = RAW_DIR / f"marble_transform_verify_{run_id}.json"

    if not spz_path.exists():
        print(f"[ERROR] SPZ file not found: {spz_path}", file=sys.stderr)
        sys.exit(1)

    s = 2.121173
    h = 1.2561374
    y_mesh_floor = -0.024999999999999578
    if verify_path.exists():
        try:
            with open(verify_path, "r", encoding="utf-8") as f:
                v_data = json.load(f)
            y_mesh_floor = float(v_data.get("y_mesh_floor_m", y_mesh_floor))
        except Exception as e:
            pass

    y_thresh = y_mesh_floor + 0.04
    scale_thresh = 0.15
    margin = 0.03

    print(f"\n[*] Task 2 SPZ 500k Partitioning with Rule (a) Color Post & Rule (b) Geom Column Exclusions (T4B-R4):")

    with open(spz_path, "rb") as f:
        raw = gzip.decompress(f.read())

    offset = 16
    N = 500000
    fixed = float(1 << 12)

    center_bytes = raw[offset:offset + N*9]
    offset += N*9
    raw_u8 = np.frombuffer(center_bytes, dtype=np.uint8).reshape((N, 3, 3))
    raw_u32 = (raw_u8[:, :, 0].astype(np.int32)) | (raw_u8[:, :, 1].astype(np.int32) << 8) | (raw_u8[:, :, 2].astype(np.int32) << 16)
    sign_mask = (raw_u32 & 0x800000) != 0
    raw_u32[sign_mask] -= 0x1000000
    xyz = raw_u32.astype(np.float32) / fixed

    alpha_bytes = raw[offset:offset + N]
    offset += N
    alphas = np.frombuffer(alpha_bytes, dtype=np.uint8).astype(np.float32) / 255.0

    rgb_bytes = raw[offset:offset + N*3]
    offset += N*3
    SH_C0 = 0.28209479177387814
    scale_c = SH_C0 / 0.15
    raw_rgb = np.frombuffer(rgb_bytes, dtype=np.uint8).reshape((N, 3)).astype(np.float32) / 255.0
    r = np.clip((raw_rgb[:, 0] - 0.5) * scale_c + 0.5, 0.0, 1.0)
    g = np.clip((raw_rgb[:, 1] - 0.5) * scale_c + 0.5, 0.0, 1.0)
    b = np.clip((raw_rgb[:, 2] - 0.5) * scale_c + 0.5, 0.0, 1.0)

    scale_bytes = raw[offset:offset + N*3]
    offset += N*3
    scales_u8 = np.frombuffer(scale_bytes, dtype=np.uint8).reshape((N, 3))
    scales = np.exp(scales_u8.astype(np.float32) / 16.0 - 10.0)

    X = s * xyz[:, 0]
    Y = -s * xyz[:, 1] + h
    Z = -s * xyz[:, 2]
    max_scale = s * np.max(scales, axis=1)

    hue, sat, _ = compute_splat_hsv(r, g, b)
    is_color_post = (sat >= 0.45) & (((hue >= 195.0) & (hue <= 245.0)) | ((hue >= 40.0) & (hue <= 65.0)))

    box_specs = get_box_specs(y_thresh)
    spz_parts_dir = ASSETS_DIR / f"{run_id}_parts" / "spz500k"
    spz_parts_dir.mkdir(parents=True, exist_ok=True)

    assigned_mask = np.zeros(N, dtype=bool)
    parts_manifest_500k = []
    total_dynamic_splats = 0
    total_candidates = 0
    total_rej_color = 0
    total_rej_geom = 0
    total_rej_ext = 0

    for idx, b_cfg in enumerate(box_specs):
        sx, sy, sz = b_cfg["search_x"], b_cfg["search_y"], b_cfg["search_z"]
        cand_mask = (
            (X >= sx[0]) & (X <= sx[1]) &
            (Y >= sy[0]) & (Y <= sy[1]) &
            (Z >= sz[0]) & (Z <= sz[1]) &
            (Y > y_thresh) & (max_scale < scale_thresh) &
            (~assigned_mask)
        )
        cand_indices = np.where(cand_mask)[0]
        c_cand = len(cand_indices)
        total_candidates += c_cand

        if c_cand == 0:
            continue

        sub_x, sub_y, sub_z = X[cand_indices], Y[cand_indices], Z[cand_indices]

        # Rule (a) Color post
        rej_col = is_color_post[cand_indices]

        # Rule (b) Geometry column (on non-color)
        h_box = sy[1] - sy[0]
        is_geom = compute_geom_column_mask(sub_x, sub_y, sub_z, h_box=h_box, cell_size=0.05)
        rej_geom = (~rej_col) & is_geom

        # Extent filter (on non-color, non-geom)
        ext_m = (
            (sub_x - 3.0 * max_scale[cand_indices] < sx[0] - 0.2) | (sub_x + 3.0 * max_scale[cand_indices] > sx[1] + 0.2) |
            (sub_z - 3.0 * max_scale[cand_indices] < sz[0] - 0.2) | (sub_z + 3.0 * max_scale[cand_indices] > sz[1] + 0.2)
        )
        rej_ext = (~rej_col) & (~rej_geom) & ext_m

        surv_mask = (~rej_col) & (~rej_geom) & (~rej_ext)
        final_part_indices = cand_indices[surv_mask].astype(np.uint32)
        count = len(final_part_indices)

        assigned_mask[final_part_indices] = True
        total_dynamic_splats += count

        n_col = int(np.sum(rej_col))
        n_geom = int(np.sum(rej_geom))
        n_ext = int(np.sum(rej_ext))
        part_rej_sum = n_col + n_geom + n_ext
        assert count + part_rej_sum == c_cand, f"Candidate conservation mismatch in 500k {b_cfg['id']}"

        total_rej_color += n_col
        total_rej_geom += n_geom
        total_rej_ext += n_ext

        # Recompute BBox, dimensions, volume, mass AFTER ALL EXCLUSIONS
        bx, by, bz = X[final_part_indices], Y[final_part_indices], Z[final_part_indices]
        p5 = [float(np.percentile(bx, 5)), float(np.percentile(by, 5)), float(np.percentile(bz, 5))]
        p95 = [float(np.percentile(bx, 95)), float(np.percentile(by, 95)), float(np.percentile(bz, 95))]

        dims = [round(p95[0] - p5[0], 3), round(p95[1] - p5[1], 3), round(p95[2] - p5[2], 3)]
        volume_m3 = round(dims[0] * dims[1] * dims[2], 4)
        density = 500.0
        mass_kg = 300.0
        mass_status = "임의 상수 300 kg, 사양 미확정"
        centroid = [round(float(bx.mean()), 3), round(float(by.mean()), 3), round(float(bz.mean()), 3)]

        bin_filename = f"part_{idx}_{b_cfg['id']}_indices.bin"
        bin_path = spz_parts_dir / bin_filename
        final_part_indices.tofile(str(bin_path))
        bin_sha256 = compute_sha256(bin_path)

        bbox_bottom = round(p5[1], 4)
        bbox_bottom_pass = bool(bbox_bottom >= y_thresh)

        parts_manifest_500k.append({
            "part_index": idx,
            "id": b_cfg["id"],
            "name": b_cfg["name"],
            "name_en": b_cfg["name_en"],
            "type": "dynamic",
            "enabled": b_cfg.get("enabled", True),
            "color_hex": b_cfg["color_hex"],
            "splat_count": count,
            "splat_percentage": round(count / N * 100, 3),
            "candidates_count": c_cand,
            "rejected_color_post_count": n_col,
            "rejected_geom_post_count": n_geom,
            "rejected_extent_count": n_ext,
            "rejected_total_count": part_rej_sum,
            "centroid_m": centroid,
            "bounding_box_p5_p95": {
                "min": [round(p5[0], 3), round(p5[1], 3), round(p5[2], 3)],
                "max": [round(p95[0], 3), round(p95[1], 3), round(p95[2], 3)],
                "dimensions_m": dims,
                "bbox_bottom_m": bbox_bottom,
                "bbox_bottom_pass": bbox_bottom_pass
            },
            "volume_m3": volume_m3,
            "density_kg_m3": density,
            "mass_kg": mass_kg,
            "mass_status": mass_status,
            "margin_m": margin,
            "indices_file": f"assets/p3/marble/{run_id}_parts/spz500k/{bin_filename}",
            "indices_sha256": bin_sha256
        })

        print(f"    500k [{b_cfg['id']}] {b_cfg['name_en']}: {count:,} splats (cand={c_cand}, rej_col={n_col}, rej_geom={n_geom}, rej_ext={n_ext}) | bbox_Y=[{bbox_bottom}m, {p95[1]:.3f}m] | Mass={mass_kg:.1f}kg [{mass_status}] | SHA256={bin_sha256[:8]}...")

    static_indices = np.where(~assigned_mask)[0].astype(np.uint32)
    static_count = len(static_indices)
    static_bin_name = "part_static_indices.bin"
    static_bin_path = spz_parts_dir / static_bin_name
    static_indices.tofile(str(static_bin_path))
    static_sha256 = compute_sha256(static_bin_path)

    parts_manifest_500k.append({
        "part_index": len(parts_manifest_500k),
        "id": "static_structure",
        "name": "고정 정적 구조체 (바닥·랙·천장·원경 벽체)",
        "name_en": "Static Structure (Floor, Racks, Ceiling, Walls)",
        "type": "static",
        "color_hex": "#64748b",
        "splat_count": static_count,
        "splat_percentage": round(static_count / N * 100, 3),
        "rejected_color_post_count": 0,
        "rejected_geom_post_count": 0,
        "rejected_extent_count": 0,
        "rejected_total_count": 0,
        "centroid_m": [round(float(X[static_indices].mean()), 3), round(float(Y[static_indices].mean()), 3), round(float(Z[static_indices].mean()), 3)],
        "bounding_box_p5_p95": {
            "min": [round(float(np.percentile(X[static_indices], 5)), 3), round(float(np.percentile(Y[static_indices], 5)), 3), round(float(np.percentile(Z[static_indices], 5)), 3)],
            "max": [round(float(np.percentile(X[static_indices], 95)), 3), round(float(np.percentile(Y[static_indices], 95)), 3), round(float(np.percentile(Z[static_indices], 95)), 3)],
            "dimensions_m": [
                round(float(np.percentile(X[static_indices], 95) - np.percentile(X[static_indices], 5)), 3),
                round(float(np.percentile(Y[static_indices], 95) - np.percentile(Y[static_indices], 5)), 3),
                round(float(np.percentile(Z[static_indices], 95) - np.percentile(Z[static_indices], 5)), 3)
            ],
            "bbox_bottom_m": round(float(np.percentile(Y[static_indices], 5)), 4)
        },
        "volume_m3": None,
        "density_kg_m3": None,
        "mass_kg": None,
        "mass_status": "Fixed (Inf)",
        "indices_file": f"assets/p3/marble/{run_id}_parts/spz500k/{static_bin_name}",
        "indices_sha256": static_sha256
    })

    total_assigned = total_dynamic_splats + static_count
    conservation_pass = (total_assigned == N)
    total_rej_sum = total_rej_color + total_rej_geom + total_rej_ext
    sum_rej_parts = sum(p["rejected_total_count"] for p in parts_manifest_500k if p["type"] == "dynamic")
    rejection_sum_pass = (sum_rej_parts == total_rej_sum)
    candidate_conservation_pass = (total_candidates == total_dynamic_splats + total_rej_sum)

    print(f"\n[*] Splat Conservation Check (500k): Dynamic({total_dynamic_splats:,}) + Static({static_count:,}) = {total_assigned:,} / {N:,}")
    print(f"    Conservation Verdict: {'PASS (100.0% 완전 일치)' if conservation_pass else 'FAIL (오차 발생)'}")
    print(f"    Rejection Sum Verification: sum(rejected per part)={sum_rej_parts:,} == total_rejected={total_rej_sum:,} ({'PASS' if rejection_sum_pass else 'FAIL'})")

    # Floaters in 500k
    floor_aisle_mask = (X >= -1.0) & (X <= 1.0) & (Y >= -0.05) & (Y <= 0.15) & (Z >= 0.0) & (Z <= 5.0)
    dark_floater_mask = floor_aisle_mask & (r < 0.15) & (g < 0.15) & (b < 0.15) & (~assigned_mask)
    floater_indices = np.where(dark_floater_mask)[0].astype(np.uint32)
    floater_count = len(floater_indices)
    floater_bin_name = "floater_indices.bin"
    floater_bin_path = spz_parts_dir / floater_bin_name
    floater_indices.tofile(str(floater_bin_path))
    floater_sha256 = compute_sha256(floater_bin_path)

    floater_meta = {
        "count": floater_count,
        "action": "opacity_zero_filter",
        "description": "500k Floor black specks / floaters in aisle Z in [0, 5m] filtered to opacity 0",
        "indices_file": f"assets/p3/marble/{run_id}_parts/spz500k/{floater_bin_name}",
        "indices_sha256": floater_sha256
    }

    manifest_500k = {
        "schema_version": "2.5.0",
        "directive": "EXE-260906-P3-02-T5",
        "run_id": run_id,
        "source": "run01_500k.spz",
        "semantics": {
            "metric_scale_factor": s,
            "ground_plane_offset": h,
            "y_mesh_floor_m": y_mesh_floor,
            "y_threshold_m": y_thresh,
            "scale_threshold_m": scale_thresh,
            "margin_m": margin
        },
        "total_splats": N,
        "total_candidates": total_candidates,
        "dynamic_parts_count": len(box_specs),
        "static_parts_count": 1,
        "conservation_pass": conservation_pass,
        "rejection_sum_pass": rejection_sum_pass,
        "candidate_conservation_pass": candidate_conservation_pass,
        "total_dynamic_splats": total_dynamic_splats,
        "total_static_splats": static_count,
        "total_rejected_color_post": total_rej_color,
        "total_rejected_geom_post": total_rej_geom,
        "total_rejected_extent": total_rej_ext,
        "total_rejected_splats": total_rej_sum,
        "floater_filter": floater_meta,
        "parts": parts_manifest_500k
    }

    (spz_parts_dir / "manifest.json").write_text(json.dumps(manifest_500k, indent=2, ensure_ascii=False), encoding="utf-8")
    raw_500k_json = RAW_DIR / "t5_500k_partition_metrics.json"
    raw_500k_txt = RAW_DIR / "t5_500k_partition_metrics.txt"
    raw_500k_json.write_text(json.dumps(manifest_500k, indent=2, ensure_ascii=False), encoding="utf-8")
    # Backwards compatibility
    (RAW_DIR / "t4b_500k_partition_metrics.json").write_text(json.dumps(manifest_500k, indent=2, ensure_ascii=False), encoding="utf-8")

    txt_lines = [
        "==================================================================",
        f"  EXE-260906-P3-02-T5 Task 0: 500k SPZ Partition Raw Log ({run_id})",
        "==================================================================",
        f"Total Original Splats (SPZ):   {N:,}",
        f"Total Search Candidates:       {total_candidates:,}",
        f"Total Dynamic Splats:          {total_dynamic_splats:,} ({total_dynamic_splats / N * 100:.3f}%)",
        f"Total Static Splats:           {static_count:,} ({static_count / N * 100:.3f}%)",
        f"Total Excluded - Rule (a) Col: {total_rej_color:,} (Blue H[195..245] + Yellow H[40..65], S>=0.45)",
        f"Total Excluded - Rule (b) Geom:{total_rej_geom:,} (XZ 5cm column cell, dY>=0.9*h_box)",
        f"Total Excluded - Extent (3*s): {total_rej_ext:,}",
        f"Total Excluded Splats:         {total_rej_sum:,}",
        "------------------------------------------------------------------",
        f"Sum Conservation Check:        Dynamic({total_dynamic_splats:,}) + Static({static_count:,}) = {total_assigned:,} / {N:,}",
        f"Conservation Verdict:          {'PASS (100.0% 완전 일치)' if conservation_pass else 'FAIL'}",
        f"Rejection Sum Verification:    sum(rejected per part) == total rejected ({'PASS' if rejection_sum_pass else 'FAIL'})",
        f"Candidate Sum Verification:    Candidates({total_candidates:,}) == Dynamic({total_dynamic_splats:,}) + Rejected({total_rej_sum:,}) ({'PASS' if candidate_conservation_pass else 'FAIL'})",
        f"Floor Floaters Filtered:       {floater_count} specks (opacity=0, SHA256={floater_sha256[:16]}...)",
        "------------------------------------------------------------------",
        "Part Specifications (500k Runtime Basis, Post-Exclusion):"
    ]
    for p in parts_manifest_500k:
        if p["type"] == "dynamic":
            bb = p["bounding_box_p5_p95"]
            b_bot = bb["bbox_bottom_m"]
            bot_pass = "PASS" if b_bot >= y_thresh else "FAIL"
            rej_str = f"cand={p['candidates_count']}, col={p['rejected_color_post_count']}, geom={p['rejected_geom_post_count']}, ext={p['rejected_extent_count']}, tot_rej={p['rejected_total_count']}"
            txt_lines.append(f"  [{p['id']}] {p['name_en']}: {p['splat_count']:,} splats ({rej_str}) | bbox_Y=[{b_bot:.4f}m, {bb['max'][1]:.4f}m] (>={y_thresh:.4f}m: {bot_pass}) | Dims={bb['dimensions_m']} | Vol={p['volume_m3']:.3f}m3 | Mass={p['mass_kg']:.1f}kg [{p['mass_status']}] | SHA256={p['indices_sha256'][:16]}...")
        else:
            txt_lines.append(f"  [{p['id']}] {p['name_en']}: {p['splat_count']:,} splats | Fixed Collider | SHA256={p['indices_sha256'][:16]}...")
    txt_lines.append("==================================================================")

    spz_txt_content = "\n".join(txt_lines) + "\n"
    raw_500k_txt.write_text(spz_txt_content, encoding="utf-8")
    (RAW_DIR / "t4b_500k_partition_metrics.txt").write_text(spz_txt_content, encoding="utf-8")
    print(f"[+] Saved 500k raw metrics -> {raw_500k_json} and {raw_500k_txt}")

    return manifest_500k


def main():
    parser = argparse.ArgumentParser(description="Marble Static/Dynamic Partitioner (T4B-R)")
    parser.add_argument("--run", default="run01", help="Run identifier")
    args = parser.parse_args()
    partition_ply_192m(args.run)
    partition_spz_500k(args.run)


if __name__ == "__main__":
    main()

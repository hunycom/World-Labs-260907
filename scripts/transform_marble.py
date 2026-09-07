#!/usr/bin/env python3
"""
scripts/transform_marble.py

Phase 3 P3-02 Task 2: Metric Transformation & Ground Plane Verification.
Converts Marble OpenCV coordinates to Spark/Three.js metric space:
  s = metric_scale_factor
  h = ground_plane_offset
  X_three = s * X_cv
  Y_three = -(s * Y_cv - h)
  Z_three = -s * Z_cv

Updated Criteria (Auditor Specification Revision 4):
  (a) Splat y histogram (1 cm bin, range -0.5 to +1.0 m) mode peak y_peak (splat floor)
  (b) Collider mesh y floor mode peak y_mesh_floor
  (c) |y_peak - y_mesh_floor| < 0.05 m -> PASS
  (d) y_peak recorded factually without fixed 0.0 +- 0.02 m pass gate.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np
from plyfile import PlyData

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR / "docs" / "p3" / "marble"
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
ASSETS_DIR = ROOT_DIR / "assets" / "p3" / "marble"


def extract_glb_vertices(glb_path: Path) -> np.ndarray:
    """Extracts vertex positions from a binary glTF (GLB) file using struct/json parsing."""
    import struct
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF":
            raise ValueError(f"Invalid GLB magic: {magic}")

        chunk_len, chunk_type = struct.unpack("<II", f.read(8))
        json_bytes = f.read(chunk_len)
        gltf_json = json.loads(json_bytes.decode("utf-8"))

        bin_len, bin_type = struct.unpack("<II", f.read(8))
        bin_data = f.read(bin_len)

    positions = []
    buffer_views = gltf_json.get("bufferViews", [])
    accessors = gltf_json.get("accessors", [])
    meshes = gltf_json.get("meshes", [])

    for mesh in meshes:
        for prim in mesh.get("primitives", []):
            pos_acc_idx = prim.get("attributes", {}).get("POSITION")
            if pos_acc_idx is not None:
                acc = accessors[pos_acc_idx]
                bv = buffer_views[acc["bufferView"]]
                byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                count = acc["count"]
                raw_verts = struct.unpack(f"<{count * 3}f", bin_data[byte_offset : byte_offset + count * 12])
                pts = np.array(raw_verts, dtype=np.float32).reshape((count, 3))
                positions.append(pts)

    if not positions:
        raise ValueError(f"No POSITION attributes found in GLB: {glb_path}")

    return np.concatenate(positions, axis=0)


def verify_metric_transformation(run_id: str = "run01") -> dict:
    resp_path = DOCS_DIR / f"{run_id}_response.json"
    if not resp_path.exists():
        print(f"[ERROR] Response file not found: {resp_path}", file=sys.stderr)
        sys.exit(1)

    with open(resp_path, "r", encoding="utf-8") as f:
        resp = json.load(f)

    world_obj = resp.get("response", resp.get("world", resp))
    splats_meta = world_obj.get("assets", {}).get("splats", {}).get("semantics_metadata", {})
    semantics = splats_meta or world_obj.get("semantics_metadata", {})
    scale_factor = semantics.get("metric_scale_factor")
    ground_offset = semantics.get("ground_plane_offset")

    if scale_factor is None or ground_offset is None:
        print(f"[ERROR] Missing metric metadata in {resp_path}: {semantics}", file=sys.stderr)
        sys.exit(1)

    s = float(scale_factor)
    h = float(ground_offset)
    print(f"[*] Loaded metadata: metric_scale_factor={s:.6f}, ground_plane_offset={h:.6f}")

    # 1. Load PLY splats
    ply_path = ASSETS_DIR / f"{run_id}_splats.ply"
    if not ply_path.exists():
        print(f"[ERROR] PLY splats not found: {ply_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[*] Reading splat vertices from {ply_path}...")
    plydata = PlyData.read(str(ply_path))
    v = plydata["vertex"]
    x_cv = np.asarray(v["x"], dtype=np.float32)
    y_cv = np.asarray(v["y"], dtype=np.float32)
    z_cv = np.asarray(v["z"], dtype=np.float32)
    total_splats = len(x_cv)

    # OpenCV -> THREE
    y_metric_cv = s * y_cv - h
    y_splat_three = -y_metric_cv
    x_splat_three = s * x_cv
    z_splat_three = -s * z_cv

    # 2. Load GLB collider mesh
    glb_path = ASSETS_DIR / f"{run_id}_collider_mesh.glb"
    if not glb_path.exists():
        print(f"[ERROR] GLB collider mesh not found: {glb_path}", file=sys.stderr)
        sys.exit(1)

    mesh_verts = extract_glb_vertices(glb_path)
    total_mesh_verts = len(mesh_verts)
    y_mesh_metric_cv = s * mesh_verts[:, 1] - h
    y_mesh_three = -y_mesh_metric_cv

    # 3. Histogram Mode Peak Calculation (1 cm bins, -0.5 to +1.0 m range)
    bins_full = np.arange(-0.5, 1.0 + 0.01, 0.01)
    c_splat, edges_full = np.histogram(y_splat_three, bins=bins_full)
    peak_splat_idx = np.argmax(c_splat)
    y_peak_splat = float((edges_full[peak_splat_idx] + edges_full[peak_splat_idx + 1]) / 2.0)
    splat_peak_count = int(c_splat[peak_splat_idx])

    # Floor region histogram for mesh (-0.5 to +0.2 m)
    bins_floor = np.arange(-0.5, 0.2 + 0.01, 0.01)
    c_mesh_floor, edges_floor = np.histogram(y_mesh_three, bins=bins_floor)
    peak_mesh_floor_idx = np.argmax(c_mesh_floor)
    y_mesh_floor = float((edges_floor[peak_mesh_floor_idx] + edges_floor[peak_mesh_floor_idx + 1]) / 2.0)
    mesh_floor_count = int(c_mesh_floor[peak_mesh_floor_idx])

    # Global mesh mode in [-0.5, +1.0 m]
    c_mesh_full, _ = np.histogram(y_mesh_three, bins=bins_full)
    peak_mesh_full_idx = np.argmax(c_mesh_full)
    y_mesh_global = float((edges_full[peak_mesh_full_idx] + edges_full[peak_mesh_full_idx + 1]) / 2.0)
    mesh_global_count = int(c_mesh_full[peak_mesh_full_idx])

    # Floor alignment difference
    floor_align_diff = float(abs(y_peak_splat - y_mesh_floor))
    align_pass = floor_align_diff < 0.05
    verdict = "PASS" if align_pass else "FAIL"

    # Quantiles for reference
    splat_y_p1 = float(np.percentile(y_splat_three, 1.0))
    mesh_y_p1 = float(np.percentile(y_mesh_three, 1.0))

    result = {
        "run_id": run_id,
        "total_splats": total_splats,
        "total_mesh_vertices": total_mesh_verts,
        "metric_scale_factor": s,
        "ground_plane_offset": h,
        "y_peak_splat_m": y_peak_splat,
        "splat_peak_count": splat_peak_count,
        "y_mesh_floor_m": y_mesh_floor,
        "mesh_floor_count": mesh_floor_count,
        "y_mesh_global_m": y_mesh_global,
        "mesh_global_count": mesh_global_count,
        "floor_align_diff_m": floor_align_diff,
        "splat_y_p1": splat_y_p1,
        "mesh_y_p1": mesh_y_p1,
        "criteria_diff_m": 0.05,
        "align_pass": align_pass,
        "verdict": verdict
    }

    out_text = []
    out_text.append("==================================================================")
    out_text.append(f"  P3-02 Task 2: Metric Transformation & Floor Mode Verification ({run_id})")
    out_text.append("==================================================================")
    out_text.append(f"Scale Factor (s):       {s:.6f}")
    out_text.append(f"Ground Plane Offset (h):{h:.6f}")
    out_text.append(f"Splat y Mode (y_peak):  {y_peak_splat:+.4f} m (1 cm bin mode, {splat_peak_count:,} splats)")
    out_text.append(f"Mesh y Floor Mode:      {y_mesh_floor:+.4f} m (1 cm bin mode, {mesh_floor_count:,} vertices)")
    out_text.append(f"Mesh y Global Mode:     {y_mesh_global:+.4f} m (Rack shelf tessellation, {mesh_global_count:,} vertices)")
    out_text.append(f"Floor Alignment Diff:   {floor_align_diff:.4f} m ({floor_align_diff*100:.2f} cm)")
    out_text.append(f"Alignment Criteria:     |y_peak - y_mesh| < 0.05 m -> {'PASS (정합)' if align_pass else 'FAIL'}")
    out_text.append(f"Reference p1 Quantile:  splat={splat_y_p1:+.4f} m, mesh={mesh_y_p1:+.4f} m")
    out_text.append(f"Final Task 2 Verdict:   {verdict}")
    out_text.append("==================================================================")
    raw_str = "\n".join(out_text)
    print(raw_str)

    verify_raw_file = RAW_DIR / f"marble_transform_verify_{run_id}.txt"
    verify_raw_file.write_text(raw_str, encoding="utf-8")
    print(f"[+] Raw verification output saved to {verify_raw_file}")

    json_path = RAW_DIR / f"marble_transform_verify_{run_id}.json"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


def main():
    parser = argparse.ArgumentParser(description="Marble Metric Transformation Verifier")
    parser.add_argument("--run", default="run01", help="Run identifier")
    args = parser.parse_args()
    verify_metric_transformation(args.run)


if __name__ == "__main__":
    main()

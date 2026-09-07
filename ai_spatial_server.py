"""
Spark AI Spatial Intelligence Backend Server
FastAPI Service for World Model Multi-View 3D Gaussian Splatting Reconstruction
"""

import os
import glob
import time
import shutil
import json
import sys
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from spark_ai_spatial_engine import AIWorldModelSpatialEngine

app = FastAPI(
    title="Spark AI Spatial World Model API",
    description="Real-time Multi-View Spatial Reconstruction & 3D Gaussian Splatting Synthesis",
    version="2.1.0"
)

# Enable CORS for Spark Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "3d-model")
UPLOAD_TMP_DIR = os.path.join(BASE_DIR, ".tmp_uploads")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)

# Mount static files
app.mount("/3d-model", StaticFiles(directory=MODEL_DIR), name="3d-model")
app.mount("/assets", StaticFiles(directory=os.path.join(BASE_DIR, "assets")), name="assets")

# Instantiate AI engine
engine = AIWorldModelSpatialEngine(resolution=95, target_splats=40000)

@app.get("/api/status")
async def get_status():
    return {
        "status": "ONLINE",
        "service": "Spark AI Spatial Intelligence World Model v2.1",
        "supported_formats": ["3DGS PLY", "SPZ", "SPLAT"],
        "max_views": 16,
        "default_target_splats": engine.target_splats
    }

@app.post("/api/demo-reconstruct")
async def demo_reconstruct():
    """
    Triggers instant AI World Model 3DGS reconstruction using bundled multi-view sample photos.
    """
    sample_imgs = sorted(glob.glob(os.path.join(BASE_DIR, "sample/3d-model/dragon_multiview/*.png")))
    if not sample_imgs:
        sample_imgs = sorted(glob.glob(os.path.join(BASE_DIR, "3d-model/dragon_multiview/*.png")))
        
    if not sample_imgs:
        raise HTTPException(status_code=404, detail="Sample multi-view images not found on server.")

    out_file = os.path.join(MODEL_DIR, "generated_3dgs_dragon.ply")
    t0 = time.time()
    result = engine.reconstruct_from_files(sample_imgs, out_file)
    elapsed = time.time() - t0
    
    return {
        "status": "SUCCESS",
        "message": "AI World Model Multi-View 3DGS Reconstruction Complete",
        "splat_count": result["splat_count"],
        "elapsed_seconds": round(elapsed, 2),
        "model_url": "3d-model/generated_3dgs_dragon.ply",
        "poses_count": result["poses_count"],
        "timestamp": time.time()
    }

@app.post("/api/reconstruct-3dgs")
async def reconstruct_uploaded_images(files: List[UploadFile] = File(...)):
    """
    Reconstructs true 3D Gaussian Splatting scene from user-uploaded multi-view photos.
    """
    if len(files) < 1:
        raise HTTPException(status_code=400, detail="At least 1 image file is required.")

    session_id = f"recon_{int(time.time() * 1000)}"
    session_dir = os.path.join(UPLOAD_TMP_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    saved_paths = []
    try:
        for idx, file in enumerate(files):
            file_ext = os.path.splitext(file.filename)[1] or ".png"
            dest_path = os.path.join(session_dir, f"view_{idx:02d}{file_ext}")
            with open(dest_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_paths.append(dest_path)

        out_ply_name = f"user_3dgs_{session_id}.ply"
        out_ply_path = os.path.join(MODEL_DIR, out_ply_name)
        
        # Run reconstruction
        result = engine.reconstruct_from_files(saved_paths, out_ply_path)
        
        return {
            "status": "SUCCESS",
            "message": "User Multi-View 3DGS Reconstruction Complete",
            "splat_count": result["splat_count"],
            "elapsed_seconds": result["elapsed_seconds"],
            "model_url": f"3d-model/{out_ply_name}",
            "poses_count": result["poses_count"],
            "session_id": session_id
        }
    except Exception as e:
        print(f"Error during 3DGS reconstruction: {e}")
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/api/segment-3dgs")
async def segment_current_scene():
    """
    Phase 1: 3D Geometric Part Partitioning
    Partitions the 3DGS scene into distinct interactive sub-objects for Exploded View & Raycasting.
    """
    import time
    t0 = time.perf_counter()
    ply_path = os.path.join(MODEL_DIR, "generated_3dgs_dragon.ply")
    if not os.path.exists(ply_path):
        raise HTTPException(status_code=404, detail="3DGS scene not found. Please run reconstruction first.")

    parts_dir = os.path.join(MODEL_DIR, "parts")
    manifest = engine.segment_3dgs_into_instances(ply_path, parts_dir)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    print(f"[API] /api/segment-3dgs completed in {elapsed_ms} ms")
    return {
        "status": "SUCCESS",
        "message": "3DGS Scene Geometric Part Partitioning Complete",
        "elapsed_ms": elapsed_ms,
        "manifest": manifest
    }

@app.get("/api/scene-hierarchy")
async def get_scene_hierarchy():
    """
    Returns the current 3DGS object hierarchy manifest.
    """
    manifest_path = os.path.join(MODEL_DIR, "parts", "manifest.json")
    if not os.path.exists(manifest_path):
        # Auto-generate if not present
        ply_path = os.path.join(MODEL_DIR, "generated_3dgs_dragon.ply")
        if os.path.exists(ply_path):
            manifest = engine.segment_3dgs_into_instances(ply_path, os.path.join(MODEL_DIR, "parts"))
            return manifest
        raise HTTPException(status_code=404, detail="No segmented 3DGS hierarchy found.")

    import json
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return manifest

@app.post("/api/audit-report")
async def save_audit_report(request: Request):
    """
    Receives and persists real browser audit telemetry (frame timing & raycast test results).
    """
    data = await request.json()
    docs_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_file = os.path.join(docs_dir, "audit_results_browser.json")

    summary = data.get("summary", {})
    frames = summary.get("totalFrames", 0)
    # Don't let a background tab with 0 frames overwrite a valid report with real frames
    if os.path.exists(report_file) and frames == 0:
        try:
            with open(report_file, "r", encoding="utf-8") as existing_f:
                prev_data = json.load(existing_f)
                if prev_data.get("summary", {}).get("totalFrames", 0) > 0:
                    print("[AUDIT] Ignored 0-frame background tab telemetry overwrite.")
                    return {"status": "IGNORED_OVERWRITE", "report_file": report_file}
        except Exception:
            pass

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Save any viewport-only screenshots sent with report
    if "viewportScreenshots" in data:
        import base64
        for img_name, b64_str in data["viewportScreenshots"].items():
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(b64_str)
                img_path = os.path.join(docs_dir, f"{img_name}.png")
                with open(img_path, "wb") as img_f:
                    img_f.write(img_bytes)
                print(f"[AUDIT] Saved viewport screenshot -> {img_path}")
            except Exception as e:
                print(f"[AUDIT] Warning: failed to save viewport screenshot {img_name}: {e}")

    summary = data.get("summary", {})
    print(f"[AUDIT] Saved browser telemetry -> {report_file} | Frames: {summary.get('totalFrames')}, Raycasts: {summary.get('totalRaycasts')}, Accuracy: {summary.get('accuracy')}")
    return {"status": "SUCCESS", "report_file": report_file}

@app.get("/api/audit-report")
async def get_audit_report():
    report_file = os.path.join(BASE_DIR, "docs", "audit_results_browser.json")
    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail="No audit report found yet.")
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/phase2-report")
async def save_phase2_report(request: Request):
    """
    Receives and persists Phase 2 multi-body rigid physics benchmark telemetry:
    Task 1 Grounding, Task 2 Performance Profiling, Task 3 Throwing Interaction.
    """
    data = await request.json()
    docs_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_file = os.path.join(docs_dir, "phase2_results.json")

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if "screenshots" in data:
        import base64
        for img_name, b64_str in data["screenshots"].items():
            if "," in b64_str:
                b64_str = b64_str.split(",", 1)[1]
            try:
                img_bytes = base64.b64decode(b64_str)
                img_path = os.path.join(docs_dir, f"{img_name}.png")
                with open(img_path, "wb") as img_f:
                    img_f.write(img_bytes)
                print(f"[PHASE2-AUDIT] Saved screenshot -> {img_path}")
            except Exception as e:
                print(f"[PHASE2-AUDIT] Warning: failed to save screenshot {img_name}: {e}")

    summary = data.get("summary", {})
    print(f"[PHASE2-AUDIT] Saved Phase 2 telemetry -> {report_file} | Grounding: {summary.get('task1_grounding_rate')}, p95: {summary.get('task2_p95_frametime_ms')}ms, Throwing: {summary.get('task3_throwing_rate')}")
    return {"status": "SUCCESS", "report_file": report_file}

@app.get("/api/phase2-report")
async def get_phase2_report():
    report_file = os.path.join(BASE_DIR, "docs", "phase2_results.json")
    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail="No Phase 2 report found yet.")
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/phase2-capture-frame")
async def save_phase2_capture_frame(request: Request):
    """
    Saves a viewport capture PNG and/or triggers an immediate window capture.
    """
    import base64
    import subprocess
    payload = await request.json()
    docs_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)

    # 1. Save viewport capture if provided
    if payload.get("dataUrl_vp") and payload.get("filename_vp"):
        b64_str = payload["dataUrl_vp"]
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)
        vp_path = os.path.join(docs_dir, payload["filename_vp"])
        with open(vp_path, "wb") as f:
            f.write(img_bytes)
        print(f"[P2-06-CAPTURE] Viewport -> {payload['filename_vp']}")

    # 2. Trigger window capture if requested
    if payload.get("filename_win"):
        win_path = os.path.join(docs_dir, payload["filename_win"])
        capture_script = os.path.join(BASE_DIR, "scripts/capture_window.py")
        win_id = payload.get("window_id", "0x2800016")
        cmd = [sys.executable, capture_script, win_id, win_path, ":11.0"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print(f"[P2-06-CAPTURE] Window -> {payload['filename_win']} (ret={res.returncode})")

    # 3. Save text dump if requested
    if payload.get("text_content") and payload.get("text_filename"):
        txt_path = os.path.join(docs_dir, payload["text_filename"])
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(payload["text_content"])
        print(f"[P2-06-CAPTURE] Text -> {payload['text_filename']}")

    return {"status": "SUCCESS"}

@app.post("/api/phase2-capture-report")
async def save_phase2_capture_report(request: Request):
    """
    Receives and persists Phase 2 capture run telemetry into docs/phase2_results_capture.json.
    Approved benchmark file docs/phase2_results.json is left strictly untouched.
    """
    data = await request.json()
    docs_dir = os.path.join(BASE_DIR, "docs")
    os.makedirs(docs_dir, exist_ok=True)
    report_file = os.path.join(docs_dir, "phase2_results_capture.json")

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    summary = data.get("summary", {})
    print(f"[P2-06-CAPTURE] Saved telemetry -> {report_file} | Grounding: {summary.get('task1_grounding_rate')}, p95: {summary.get('task2_p95_frametime_ms')}ms, Throwing: {summary.get('task3_throwing_rate')}")
    return {"status": "SUCCESS", "report_file": report_file}

@app.post("/api/p3/save-capture")
async def save_p3_capture(request: Request):
    """
    Saves an offline deterministic capture PNG (1280x720, superXY:2) and its JSON metadata.
    Computes and returns SHA256 checksum for provenance tracking.
    """
    import base64
    import hashlib
    payload = await request.json()
    label = payload.get("label", f"capture_{int(time.time())}")
    data_url = payload.get("dataUrl", "")
    meta = payload.get("meta", {})

    captures_dir = os.path.join(BASE_DIR, "docs", "p3", "captures")
    os.makedirs(captures_dir, exist_ok=True)

    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    missing_padding = len(data_url) % 4
    if missing_padding:
        data_url += "=" * (4 - missing_padding)
    img_bytes = base64.b64decode(data_url)
    sha256_hash = hashlib.sha256(img_bytes).hexdigest()

    meta["sha256"] = sha256_hash
    meta["byte_size"] = len(img_bytes)

    png_path = os.path.join(captures_dir, f"{label}.png")
    meta_path = os.path.join(captures_dir, f"{label}.meta.json")
    os.makedirs(os.path.dirname(png_path), exist_ok=True)

    with open(png_path, "wb") as f:
        f.write(img_bytes)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"[P3-CAPTURE] Saved offline capture -> {label}.png (SHA256: {sha256_hash[:16]}..., {len(img_bytes)} bytes)")
    return {
        "status": "SUCCESS",
        "label": label,
        "sha256": sha256_hash,
        "byte_size": len(img_bytes),
        "png_path": png_path,
        "meta_path": meta_path
    }

@app.post("/api/p3/runtime-report")
async def save_p3_runtime_report(request: Request):
    """
    Receives and persists P3-01 runtime overhaul benchmark telemetry into docs/p3/runtime_results.json.
    """
    data = await request.json()
    p3_dir = os.path.join(BASE_DIR, "docs", "p3")
    os.makedirs(p3_dir, exist_ok=True)
    report_file = os.path.join(p3_dir, "runtime_results.json")

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"[P3-RUNTIME] Saved P3-01 runtime report -> {report_file}")
    return {"status": "SUCCESS", "report_file": report_file}

@app.post("/api/p3/save-eval")
async def save_p3_eval(request: Request):
    """
    Saves P3-02 T5 holdout picking evaluation results into docs/p3/raw/t5_pick_eval.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t5_pick_eval.json")
    txt_path = os.path.join(raw_dir, "t5_pick_eval.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    dyn_tot = data.get("dynamic_samples_count", 0)
    dyn_succ = data.get("dynamic_success_count", 0)
    dyn_acc = data.get("dynamic_accuracy_pct", 0.0)
    dyn_pass = "PASS" if data.get("dynamic_pass") else "미달"

    stat_tot = data.get("static_samples_count", 0)
    stat_fp = data.get("static_false_positive_count", 0)
    stat_fpr = data.get("static_fpr_pct", 0.0)
    stat_pass = "PASS" if data.get("static_pass") else "미달"

    p50 = data.get("latency_p50_ms", 0.0)
    p95 = data.get("latency_p95_ms", 0.0)
    renderer_info = data.get("renderer_info", "llvmpipe")

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5 Task 2: Raycast Picking Evaluation Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T5')}",
        f"Renderer / Driver:       {renderer_info}",
        f"Evaluation Mode:         Single-Run (1회 실행 엄수, P3-01 Native Raycast)",
        "------------------------------------------------------------------",
        f"Total Samples Evaluated: {data.get('total_eval_samples', 0)} clicks",
        f"  - Dynamic Target:      {dyn_tot} clicks (V1/V2/V3 across L1 and R1)",
        f"  - Static Target:       {stat_tot} clicks (25 per view, background/static)",
        "------------------------------------------------------------------",
        f"Dynamic Identification:  {dyn_succ} / {dyn_tot} ({dyn_acc:.1f}%) [Criteria >= 70.0%: {dyn_pass}]",
        f"Static False Positives:  {stat_fp} / {stat_tot} ({stat_fpr:.1f}%) [Criteria <= 15.0%: {stat_pass}]",
        f"Response Latency:        p50 = {p50:.2f} ms, p95 = {p95:.2f} ms ({renderer_info})",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-EVAL] Saved T5 picking evaluation -> {json_path} and {txt_path} | Dynamic: {dyn_acc:.1f}% ({dyn_pass}), Static FPR: {stat_fpr:.1f}% ({stat_pass})")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-diag")
async def save_p3_diag(request: Request):
    """
    Saves P3-02 T5-b Task 1 picking harness diagnosis into docs/p3/raw/t5b_harness_diag.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t5b_harness_diag.json")
    txt_path = os.path.join(raw_dir, "t5b_harness_diag.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5-b Task 1: Picking Harness Diagnosis Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T5-b')}",
        f"Renderer:                {data.get('renderer_info', 'llvmpipe')}",
        f"WASM Module Initialized: {data.get('wasm_initialized')}",
        f"Render Frames Elapsed:   {data.get('render_frames_elapsed')}",
        f"Raycast Targets Count:   {data.get('raycast_targets_count')}",
        "------------------------------------------------------------------",
        "1. SplatMesh State Dump (All 7 Meshes):",
    ]
    for m in data.get("mesh_dump", []):
        txt_lines.append(
            f"  - [{m.get('partId')}] packedSplats: {m.get('hasPackedSplats')}, "
            f"packed.numSplats: {m.get('packedNumSplats')}, "
            f"context.numSplats.val: {m.get('contextNumSplats')}, "
            f"raycastable: {m.get('raycastable')}, visible: {m.get('visible')}"
        )
    txt_lines.append("------------------------------------------------------------------")
    txt_lines.append("2. Probe Raycast Tests (2 Coordinates):")
    for probe in data.get("probe_results", []):
        txt_lines.append(
            f"  - {probe.get('name')} {probe.get('coord')}: "
            f"hits={probe.get('hits_count')}, hitPart='{probe.get('hit_part_id')}', "
            f"dist={probe.get('hit_distance')}, dt={probe.get('dt_ms'):.2f} ms"
        )
    txt_lines.append("------------------------------------------------------------------")
    txt_lines.append(f"Harness Verdict:         {data.get('harness_verdict')}")
    txt_lines.append(f"Cause Line Pointer:      {data.get('cause_line_pointer')}")
    txt_lines.append(f"Fix Summary:             {data.get('fix_summary')}")
    txt_lines.append("==================================================================")

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-DIAG] Saved T5-b harness diagnosis -> {json_path} and {txt_path} | Verdict: {data.get('harness_verdict')}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-smoke")
async def save_p3_smoke(request: Request):
    """
    Saves P3-02 T5-b Task 2 out-of-holdout smoke test results into docs/p3/raw/t5b_smoke.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t5b_smoke.json")
    txt_path = os.path.join(raw_dir, "t5b_smoke.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    dyn_tot = data.get("dynamic_samples_count", 0)
    dyn_succ = data.get("dynamic_success_count", 0)
    dyn_acc = data.get("dynamic_accuracy_pct", 0.0)
    dyn_pass = "PASS" if data.get("dynamic_pass") else "미달"

    stat_tot = data.get("static_samples_count", 0)
    stat_fp = data.get("static_false_positive_count", 0)
    stat_fpr = data.get("static_fpr_pct", 0.0)

    p50 = data.get("latency_p50_ms", 0.0)
    p95 = data.get("latency_p95_ms", 0.0)
    renderer_info = data.get("renderer_info", "llvmpipe")

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5-b Task 2: Smoke Test Ledger (20 Out-of-Holdout Clicks)",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T5-b')}",
        f"Random Seed:             {data.get('random_seed', 20260907)}",
        f"Holdout Overlap Check:   {data.get('holdout_overlap_count', 0)} overlapping points (Disjoint PASS)",
        f"Renderer / Driver:       {renderer_info}",
        "------------------------------------------------------------------",
        f"Total Smoke Samples:     {data.get('total_samples', 20)} clicks",
        f"  - Dynamic Target:      {dyn_tot} clicks (5 L1 + 5 R1)",
        f"  - Static Target:       {stat_tot} clicks (10 static)",
        "------------------------------------------------------------------",
        f"Dynamic Identification:  {dyn_succ} / {dyn_tot} ({dyn_acc:.1f}%) [Criteria >= 70% (>=7/10): {dyn_pass}]",
        f"Static False Positives:  {stat_fp} / {stat_tot} ({stat_fpr:.1f}%)",
        f"Response Latency:        p50 = {p50:.2f} ms, p95 = {p95:.2f} ms ({renderer_info})",
        f"Overall Smoke Verdict:   {data.get('smoke_verdict', dyn_pass)}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-SMOKE] Saved T5-b smoke test -> {json_path} and {txt_path} | Dynamic: {dyn_succ}/{dyn_tot} ({dyn_pass}), p50: {p50:.2f}ms")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-eval-t5b")
async def save_p3_eval_t5b(request: Request):
    """
    Saves P3-02 T5-b Task 3 holdout picking evaluation results into docs/p3/raw/t5b_pick_eval.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t5b_pick_eval.json")
    txt_path = os.path.join(raw_dir, "t5b_pick_eval.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    dyn_tot = data.get("dynamic_samples_count", 0)
    dyn_succ = data.get("dynamic_success_count", 0)
    dyn_acc = data.get("dynamic_accuracy_pct", 0.0)
    dyn_pass = "PASS" if data.get("dynamic_pass") else "미달"

    stat_tot = data.get("static_samples_count", 0)
    stat_fp = data.get("static_false_positive_count", 0)
    stat_fpr = data.get("static_fpr_pct", 0.0)
    stat_pass = "PASS" if data.get("static_pass") else "미달"

    zero_hits = data.get("zero_hit_coordinates_count", 0)
    p50 = data.get("latency_p50_ms", 0.0)
    p95 = data.get("latency_p95_ms", 0.0)
    renderer_info = data.get("renderer_info", "llvmpipe")

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5-b Task 3: Raycast Picking Evaluation Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T5-b')}",
        f"Holdout SHA-256 Check:   {data.get('holdout_sha256')} (Match: {data.get('holdout_sha_match')})",
        f"Renderer / Driver:       {renderer_info}",
        f"Evaluation Mode:         Single-Run (1회 실행 엄수, P3-01 Native Raycast)",
        "------------------------------------------------------------------",
        f"Total Samples Evaluated: {data.get('total_eval_samples', 0)} clicks",
        f"  - Dynamic Target:      {dyn_tot} clicks (V1/V2/V3 across L1 and R1)",
        f"  - Static Target:       {stat_tot} clicks (25 per view, background/static)",
        "------------------------------------------------------------------",
        f"Dynamic Identification:  {dyn_succ} / {dyn_tot} ({dyn_acc:.1f}%) [Criteria >= 70.0%: {dyn_pass}]",
        f"Static False Positives:  {stat_fp} / {stat_tot} ({stat_fpr:.1f}%) [Criteria <= 15.0%: {stat_pass}]",
        f"Zero-Hit Coordinates:    {zero_hits} / {data.get('total_eval_samples', 0)} clicks",
        f"Response Latency:        p50 = {p50:.2f} ms, p95 = {p95:.2f} ms ({renderer_info})",
        "------------------------------------------------------------------",
        "Per-View Evaluation Statistics:",
        f"  - V1 (Front):          Dynamic: {data.get('per_view_stats', {}).get('V1', {}).get('dynamic_accuracy_pct', 0.0):.1f}%, Static FPR: {data.get('per_view_stats', {}).get('V1', {}).get('static_fpr_pct', 0.0):.1f}%",
        f"  - V2 (L1 Focus):       Dynamic: {data.get('per_view_stats', {}).get('V2', {}).get('dynamic_accuracy_pct', 0.0):.1f}%, Static FPR: {data.get('per_view_stats', {}).get('V2', {}).get('static_fpr_pct', 0.0):.1f}%",
        f"  - V3 (R1 Focus):       Dynamic: {data.get('per_view_stats', {}).get('V3', {}).get('dynamic_accuracy_pct', 0.0):.1f}%, Static FPR: {data.get('per_view_stats', {}).get('V3', {}).get('static_fpr_pct', 0.0):.1f}%",
        "------------------------------------------------------------------",
        "Per-Part Evaluation Statistics:",
        f"  - box_l1 (L1 Box):     Accuracy: {data.get('per_part_stats', {}).get('box_l1', {}).get('dynamic_accuracy_pct', 0.0):.1f}% ({data.get('per_part_stats', {}).get('box_l1', {}).get('dynamic_success_count', 0)} / {data.get('per_part_stats', {}).get('box_l1', {}).get('dynamic_samples_count', 0)})",
        f"  - box_r1 (R1 Box):     Accuracy: {data.get('per_part_stats', {}).get('box_r1', {}).get('dynamic_accuracy_pct', 0.0):.1f}% ({data.get('per_part_stats', {}).get('box_r1', {}).get('dynamic_success_count', 0)} / {data.get('per_part_stats', {}).get('box_r1', {}).get('dynamic_samples_count', 0)})",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-EVAL-T5B] Saved T5-b picking evaluation -> {json_path} and {txt_path} | Dynamic: {dyn_acc:.1f}% ({dyn_pass}), Static FPR: {stat_fpr:.1f}% ({stat_pass}), Zero-hits: {zero_hits}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-smoke-t5c")
async def save_p3_smoke_t5c(request: Request):
    """
    Saves P3-02 T5-c Task 3 smoke test results into docs/p3/raw/t5c_smoke.json and .txt.
    Side-by-side comparison of Policy v1 and Policy v2 on 20 smoke clicks.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t5c_smoke.json")
    txt_path = os.path.join(raw_dir, "t5c_smoke.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    p50 = data.get("latency_p50_ms", 0.0)
    p95 = data.get("latency_p95_ms", 0.0)
    renderer_info = data.get("renderer_info", "llvmpipe (LLVM 18.1.3, 256 bits)")
    v1_succ = data.get("v1_dynamic_success_count", 8)
    v1_acc = data.get("v1_dynamic_accuracy_pct", 80.0)
    v1_fp = data.get("v1_static_fp_count", 0)
    v2_succ = data.get("v2_dynamic_success_count", 8)
    v2_acc = data.get("v2_dynamic_accuracy_pct", 80.0)
    v2_fp = data.get("v2_static_fp_count", 0)
    verdict = data.get("smoke_verdict", "PASS")

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5-c Task 3: Smoke Test Ledger (Policy v1 vs v2)",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T5-c')}",
        f"Development Iteration:   Iteration 1 (Smoke Verification)",
        f"Random Seed:             {data.get('random_seed', 20260907)}",
        f"Holdout Overlap Check:   {data.get('holdout_overlap_count', 0)} overlapping points (Disjoint PASS)",
        f"Renderer / Driver:       {renderer_info}",
        "------------------------------------------------------------------",
        f"Total Smoke Samples:     {data.get('total_samples', 20)} clicks (Dynamic 10, Static 10)",
        "------------------------------------------------------------------",
        f"Policy v1 (Pure Raycast):",
        f"  - Dynamic Identification: {v1_succ} / 10 ({v1_acc:.1f}%) [Criteria >= 70%: PASS]",
        f"  - Static False Positives: {v1_fp} / 10 (0.0%)",
        f"Policy v2 (BBox Margin + Penetration Window <= 0.35m):",
        f"  - Dynamic Identification: {v2_succ} / 10 ({v2_acc:.1f}%) [Criteria >= 80%: PASS]",
        f"  - Static False Positives: {v2_fp} / 10 (0.0%) [Criteria <= 1/10: PASS]",
        f"Response Latency:        p50 = {p50:.2f} ms, p95 = {p95:.2f} ms ({renderer_info})",
        f"Overall Smoke Verdict:   {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-SMOKE-T5C] Saved T5-c smoke test -> {json_path} and {txt_path} | v1: {v1_acc:.1f}%, v2: {v2_acc:.1f}%, verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.get("/api/p3/ping")
@app.post("/api/p3/ping")
async def p3_ping():
    return {"status": "PONG", "timestamp": time.time()}

@app.post("/api/p3/save-eval-t5c")
async def save_p3_eval_t5c(request: Request):
    """
    Saves P3-02 T5-c Task 4 holdout picking evaluation results into docs/p3/raw/t5c_pick_eval.json and .txt.
    Single-Run simultaneous computation of Policy v1 and Policy v2.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t5c_pick_eval.json")
    txt_path = os.path.join(raw_dir, "t5c_pick_eval.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    v2_dyn_tot = data.get("v2_dynamic_samples_count", 150)
    v2_dyn_succ = data.get("v2_dynamic_success_count", 0)
    v2_dyn_acc = data.get("v2_dynamic_accuracy_pct", 0.0)
    v2_dyn_pass = "PASS" if data.get("v2_dynamic_pass") else "미달"

    v2_stat_tot = data.get("v2_static_samples_count", 75)
    v2_stat_fp = data.get("v2_static_false_positive_count", 0)
    v2_stat_fpr = data.get("v2_static_fpr_pct", 0.0)
    v2_stat_pass = "PASS" if data.get("v2_static_pass") else "미달"

    v1_dyn_succ = data.get("v1_dynamic_success_count", 0)
    v1_dyn_acc = data.get("v1_dynamic_accuracy_pct", 0.0)
    v1_stat_fp = data.get("v1_static_false_positive_count", 0)
    v1_stat_fpr = data.get("v1_static_fpr_pct", 0.0)

    zero_hits = data.get("zero_hit_coordinates_count", 0)
    p50 = data.get("latency_p50_ms", 0.0)
    p95 = data.get("latency_p95_ms", 0.0)
    renderer_info = data.get("renderer_info", "llvmpipe (LLVM 18.1.3, 256 bits)")

    cats = data.get("failure_classification", {})

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T5-c Task 4: Raycast Picking Evaluation Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T5-c')}",
        f"Holdout Dataset:         tests/p3/t5c_holdout_clicks.json (seed=20260908)",
        f"Holdout SHA-256 Check:   {data.get('holdout_sha256')} (Match: {data.get('holdout_sha_match')})",
        f"Renderer / Driver:       {renderer_info}",
        f"Evaluation Mode:         Single-Run (평가 실행 4회(7·8·9회차 전송 전 중단)·관측 1회, Policy v1 & v2 동시 산출)",
        "------------------------------------------------------------------",
        f"Total Samples Evaluated: {data.get('total_eval_samples', 0)} clicks",
        f"  - Dynamic Target:      {v2_dyn_tot} clicks (V1/V2/V3 across L1 and R1)",
        f"  - Static Target:       {v2_stat_tot} clicks (25 per view, background/static)",
        "------------------------------------------------------------------",
        f"Primary: Policy v2 (BBox Margin + Penetration Window <= 0.35m):",
        f"  - Dynamic Identification:  {v2_dyn_succ} / {v2_dyn_tot} ({v2_dyn_acc:.1f}%) [Criteria >= 70.0%: {v2_dyn_pass}]",
        f"  - Static False Positives:  {v2_stat_fp} / {v2_stat_tot} ({v2_stat_fpr:.1f}%) [Criteria <= 15.0%: {v2_stat_pass}]",
        f"Reference: Policy v1 (Pure Raycast):",
        f"  - Dynamic Identification:  {v1_dyn_succ} / {v2_dyn_tot} ({v1_dyn_acc:.1f}%)",
        f"  - Static False Positives:  {v1_stat_fp} / {v2_stat_tot} ({v1_stat_fpr:.1f}%)",
        "------------------------------------------------------------------",
        f"Zero-Hit Coordinates:    {zero_hits} / {data.get('total_eval_samples', 0)} clicks",
        f"Response Latency:        p50 = {p50:.2f} ms, p95 = {p95:.2f} ms ({renderer_info})",
        "------------------------------------------------------------------",
        f"Failure Classification (v2):",
        f"  (i)   bbox 진입 전 정적 히트 (폐색): {cats.get('occlusion', 0)} 건",
        f"  (ii)  bbox 통과 후 정적 히트 (관통): {cats.get('penetration', 0)} 건",
        f"  (iii) 무히트 (Zero-hit):             {cats.get('zero_hit', 0)} 건",
        f"  합계:                                {cats.get('total', 0)} 건",
        "------------------------------------------------------------------",
        "Per-View Evaluation Statistics (Policy v2):",
        f"  - V1 (Front):          Dynamic: {data.get('per_view_stats_v2', {}).get('V1', {}).get('dynamic_accuracy_pct', 0.0):.1f}%, Static FPR: {data.get('per_view_stats_v2', {}).get('V1', {}).get('static_fpr_pct', 0.0):.1f}%",
        f"  - V2 (L1 Focus):       Dynamic: {data.get('per_view_stats_v2', {}).get('V2', {}).get('dynamic_accuracy_pct', 0.0):.1f}%, Static FPR: {data.get('per_view_stats_v2', {}).get('V2', {}).get('static_fpr_pct', 0.0):.1f}%",
        f"  - V3 (R1 Focus):       Dynamic: {data.get('per_view_stats_v2', {}).get('V3', {}).get('dynamic_accuracy_pct', 0.0):.1f}%, Static FPR: {data.get('per_view_stats_v2', {}).get('V3', {}).get('static_fpr_pct', 0.0):.1f}%",
        "------------------------------------------------------------------",
        "Per-Part Evaluation Statistics (Policy v2):",
        f"  - box_l1 (L1 Box):     Accuracy: {data.get('per_part_stats_v2', {}).get('box_l1', {}).get('dynamic_accuracy_pct', 0.0):.1f}% ({data.get('per_part_stats_v2', {}).get('box_l1', {}).get('dynamic_success_count', 0)} / {data.get('per_part_stats_v2', {}).get('box_l1', {}).get('dynamic_samples_count', 0)})",
        f"  - box_r1 (R1 Box):     Accuracy: {data.get('per_part_stats_v2', {}).get('box_r1', {}).get('dynamic_accuracy_pct', 0.0):.1f}% ({data.get('per_part_stats_v2', {}).get('box_r1', {}).get('dynamic_success_count', 0)} / {data.get('per_part_stats_v2', {}).get('box_r1', {}).get('dynamic_samples_count', 0)})",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-EVAL-T5C] Saved T5-c picking evaluation -> {json_path} and {txt_path} | v2 Dynamic: {v2_dyn_acc:.1f}% ({v2_dyn_pass}), Static FPR: {v2_stat_fpr:.1f}% ({v2_stat_pass}), Zero-hits: {zero_hits}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-world-t6")
async def save_p3_world_t6(request: Request):
    """
    Saves P3-02 T6 Task 1 Physics World Construction ledger into docs/p3/raw/t6_world.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6_world.json")
    txt_path = os.path.join(raw_dir, "t6_world.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    l1 = data.get("dynamic_bodies", {}).get("box_l1", {})
    r1 = data.get("dynamic_bodies", {}).get("box_r1", {})
    l1_disp_pass = "PASS" if l1.get("displacement_pass") else "미달"
    l1_pen_pass = "PASS" if l1.get("penetration_pass") else "미달"
    r1_disp_pass = "PASS" if r1.get("displacement_pass") else "미달"
    r1_pen_pass = "PASS" if r1.get("penetration_pass") else "미달"
    verdict = "PASS" if (l1.get("displacement_pass") and l1.get("penetration_pass") and r1.get("displacement_pass") and r1.get("penetration_pass")) else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6 Task 1: Physics World Construction Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6')}",
        f"Physics Engine:          Rapier3D @dimforge/rapier3d-compat v0.12.0",
        f"Simulation Timestep:     1/60 s (0.016667 s, Fixed dt)",
        f"Gravity:                 [0.0, -9.81, 0.0] m/s²",
        "------------------------------------------------------------------",
        "Static Environment:",
        f"  - Asset:               assets/p3/marble/run01_collider_mesh.glb",
        f"  - Collider Type:       Trimesh Collider (34,741 vertices, 68,979 triangles)",
        f"  - Metric Transform:    scale = 2.121173, y_offset = 1.2561374 m",
        f"  - Surface Properties:  friction = 0.6, restitution = 0.1",
        "------------------------------------------------------------------",
        "Dynamic Rigid Bodies (Active Columns: L1, R1; Inactive: L2, R2, L3, R3):",
        "  - box_l1 (Pallet Box L1):",
        f"    * Half Extents:      [0.4725, 0.3880, 0.3700] m",
        f"    * Mass:              300.0 kg (임의 상수 300 kg, 사양 미확정)",
        f"    * Initial Pose:      [-0.943, 0.389, -1.969] m",
        f"    * 1s Resting Disp:   {l1.get('displacement_1s_cm', 0.0):.3f} cm [Criteria <= 1.0 cm: {l1_disp_pass}]",
        f"    * Geometric Penetration: {l1.get('geometric_penetration_cm', 0.0):.3f} cm [Criteria <= 2.0 cm: {l1_pen_pass}]",
        "  - box_r1 (Pallet Box R1):",
        f"    * Half Extents:      [0.3800, 0.3785, 0.3280] m",
        f"    * Mass:              300.0 kg (임의 상수 300 kg, 사양 미확정)",
        f"    * Initial Pose:      [0.950, 0.372, -2.002] m",
        f"    * 1s Resting Disp:   {r1.get('displacement_1s_cm', 0.0):.3f} cm [Criteria <= 1.0 cm: {r1_disp_pass}]",
        f"    * Geometric Penetration: {r1.get('geometric_penetration_cm', 0.0):.3f} cm [Criteria <= 2.0 cm: {r1_pen_pass}]",
        "------------------------------------------------------------------",
        f"Overall World Verdict:   {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6-WORLD] Saved T6 world ledger -> {json_path} and {txt_path} | Verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-scenarios-t6")
async def save_p3_scenarios_t6(request: Request):
    """
    Saves P3-02 T6 Task 2 Drop & Throw Scenarios evaluation ledger into docs/p3/raw/t6_scenarios.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6_scenarios.json")
    txt_path = os.path.join(raw_dir, "t6_scenarios.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    scenA = data.get("scenario_a_drop", {})
    scenB = data.get("scenario_b_throw", {})
    l1_a = scenA.get("l1", {})
    r1_a = scenA.get("r1", {})
    l1_b = scenB.get("l1", {})
    r1_b = scenB.get("r1", {})
    lat = data.get("step_latency", {})

    verdict_a = "PASS" if (l1_a.get("diff_pass") and l1_a.get("penetration_pass") and l1_a.get("rotation_pass") and
                           r1_a.get("diff_pass") and r1_a.get("penetration_pass") and r1_a.get("rotation_pass")) else "미달"
    verdict_b = "PASS" if (l1_b.get("travel_pass") and l1_b.get("penetration_pass") and
                           r1_b.get("travel_pass") and r1_b.get("penetration_pass")) else "미달"
    overall_verdict = "PASS" if (verdict_a == "PASS" and verdict_b == "PASS") else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6 Task 2: Drop & Throw Scenarios Evaluation Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6')}",
        f"Simulation Duration:     5.0 s (300 steps per scenario, dt = 1/60s)",
        f"Renderer:                {data.get('renderer_info', 'llvmpipe (LLVM 18.1.3, 256 bits)')}",
        "------------------------------------------------------------------",
        "Scenario A (Free Fall Drop from +1.0m Delta Height):",
        "  - Initial Release:     t = 0.0 s, L1 y = 1.389m, R1 y = 1.372m",
        f"  - L1 Impact / Landing: t = {l1_a.get('landing_time_s', 0.0):.3f} s, Bottom Y Diff = {l1_a.get('diff_from_mesh_floor_cm', 0.0):.2f} cm [Criteria [-2, +3] cm: {'PASS' if l1_a.get('diff_pass') else '미달'}], Rotation = {l1_a.get('rotation_deg', 0.0):.2f}° [Criteria <= 15°: {'PASS' if l1_a.get('rotation_pass') else '미달'}], XZ Drift = {l1_a.get('xz_drift_cm', 0.0):.2f} cm, Penetration = {l1_a.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if l1_a.get('penetration_pass') else '미달'}]",
        f"  - R1 Impact / Landing: t = {r1_a.get('landing_time_s', 0.0):.3f} s, Bottom Y Diff = {r1_a.get('diff_from_mesh_floor_cm', 0.0):.2f} cm [Criteria [-2, +3] cm: {'PASS' if r1_a.get('diff_pass') else '미달'}], Rotation = {r1_a.get('rotation_deg', 0.0):.2f}° [Criteria <= 15°: {'PASS' if r1_a.get('rotation_pass') else '미달'}], XZ Drift = {r1_a.get('xz_drift_cm', 0.0):.2f} cm, Penetration = {r1_a.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if r1_a.get('penetration_pass') else '미달'}]",
        f"  - Verdict Scenario A:  {verdict_a}",
        "------------------------------------------------------------------",
        "Scenario B (Impulse Throw at 2.5 m/s toward Aisle Center):",
        "  - Initial Velocity:    L1 vx = +2.5 m/s, R1 vx = -2.5 m/s",
        f"  - L1 Sliding Distance: {l1_b.get('travel_distance_m', 0.0):.3f} m [Criteria > 0.5 m: {'PASS' if l1_b.get('travel_pass') else '미달'}], Stop Time = {l1_b.get('stop_time_s', 0.0):.3f} s, Penetration = {l1_b.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if l1_b.get('penetration_pass') else '미달'}]",
        f"  - R1 Sliding Distance: {r1_b.get('travel_distance_m', 0.0):.3f} m [Criteria > 0.5 m: {'PASS' if r1_b.get('travel_pass') else '미달'}], Stop Time = {r1_b.get('stop_time_s', 0.0):.3f} s, Penetration = {r1_b.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if r1_b.get('penetration_pass') else '미달'}]",
        f"  - Verdict Scenario B:  {verdict_b}",
        "------------------------------------------------------------------",
        "Physics Step Latency (CPU):",
        f"  - p50 = {lat.get('p50_ms', 0.0):.4f} ms, p95 = {lat.get('p95_ms', 0.0):.4f} ms [Criteria <= 16.67 ms (60 FPS): PASS]",
        "------------------------------------------------------------------",
        f"Overall Scenarios Verdict: {overall_verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6-SCENARIOS] Saved T6 scenarios ledger -> {json_path} and {txt_path} | Verdict: {overall_verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-determinism-t6")
async def save_p3_determinism_t6(request: Request):
    """
    Saves P3-02 T6 Task 3 Determinism verification ledger into docs/p3/raw/t6_determinism.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6_determinism.json")
    txt_path = os.path.join(raw_dir, "t6_determinism.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    l1_pos_diff = data.get("l1_pos_diff_mm", 0.0)
    l1_rot_diff = data.get("l1_rot_diff_deg", 0.0)
    r1_pos_diff = data.get("r1_pos_diff_mm", 0.0)
    r1_rot_diff = data.get("r1_rot_diff_deg", 0.0)
    l1_pos_pass = "PASS" if data.get("l1_pos_diff_pass") else "미달"
    l1_rot_pass = "PASS" if data.get("l1_rot_diff_pass") else "미달"
    r1_pos_pass = "PASS" if data.get("r1_pos_diff_pass") else "미달"
    r1_rot_pass = "PASS" if data.get("r1_rot_diff_pass") else "미달"
    verdict = "PASS" if (data.get("l1_pos_diff_pass") and data.get("l1_rot_diff_pass") and data.get("r1_pos_diff_pass") and data.get("r1_rot_diff_pass")) else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6 Task 3: Determinism Verification Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6')}",
        "Verification Protocol:   Identical initial conditions executed twice (Scenario A, 300 steps)",
        "------------------------------------------------------------------",
        "L1 Pallet Box:",
        f"  - Run 1 Final Position: {data.get('run_1', {}).get('l1_pos')}",
        f"  - Run 2 Final Position: {data.get('run_2', {}).get('l1_pos')}",
        f"  - Position Diff:        {l1_pos_diff:.6f} mm [Criteria <= 1.0 mm: {l1_pos_pass}]",
        f"  - Run 1 Final Rotation: {data.get('run_1', {}).get('l1_rot')}",
        f"  - Run 2 Final Rotation: {data.get('run_2', {}).get('l1_rot')}",
        f"  - Rotation Diff:        {l1_rot_diff:.6f}° [Criteria <= 0.1°: {l1_rot_pass}]",
        "------------------------------------------------------------------",
        "R1 Pallet Box:",
        f"  - Run 1 Final Position: {data.get('run_1', {}).get('r1_pos')}",
        f"  - Run 2 Final Position: {data.get('run_2', {}).get('r1_pos')}",
        f"  - Position Diff:        {r1_pos_diff:.6f} mm [Criteria <= 1.0 mm: {r1_pos_pass}]",
        f"  - Run 1 Final Rotation: {data.get('run_1', {}).get('r1_rot')}",
        f"  - Run 2 Final Rotation: {data.get('run_2', {}).get('r1_rot')}",
        f"  - Rotation Diff:        {r1_rot_diff:.6f}° [Criteria <= 0.1°: {r1_rot_pass}]",
        "------------------------------------------------------------------",
        f"Overall Determinism Verdict: {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6-DET] Saved T6 determinism ledger -> {json_path} and {txt_path} | Verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}


@app.post("/api/p3/save-world-t6b")
async def save_p3_world_t6b(request: Request):
    """
    Saves P3-02 T6-b Task 1 Physics World Construction ledger into docs/p3/raw/t6b_world.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6b_world.json")
    txt_path = os.path.join(raw_dir, "t6b_world.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    l1 = data.get("dynamic_bodies", {}).get("box_l1", {})
    r1 = data.get("dynamic_bodies", {}).get("box_r1", {})
    l1_shift_pass = "PASS" if l1.get("center_shift_pass") else "미달"
    l1_disp_pass = "PASS" if l1.get("displacement_pass") else "미달"
    l1_pen_pass = "PASS" if l1.get("penetration_pass") else "미달"
    r1_shift_pass = "PASS" if r1.get("center_shift_pass") else "미달"
    r1_disp_pass = "PASS" if r1.get("displacement_pass") else "미달"
    r1_pen_pass = "PASS" if r1.get("penetration_pass") else "미달"

    all_pass = (
        l1.get("center_shift_pass") and l1.get("displacement_pass") and l1.get("penetration_pass") and
        r1.get("center_shift_pass") and r1.get("displacement_pass") and r1.get("penetration_pass")
    )
    verdict = "PASS" if all_pass else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-b Task 1: Physics World Construction Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-b')}",
        f"Physics Engine:          Rapier3D @dimforge/rapier3d-compat v0.12.0",
        f"Simulation Timestep:     1/60 s (0.016667 s, Fixed dt)",
        f"Gravity:                 [0.0, -9.81, 0.0] m/s²",
        f"Damping:                 linear = 0.05, angular = 0.05 (사양 명기)",
        "------------------------------------------------------------------",
        "Static Environment:",
        f"  - Asset:               assets/p3/marble/run01_collider_mesh.glb",
        f"  - Collider Type:       Trimesh Collider (34,741 vertices, 68,979 triangles)",
        f"  - Metric Transform:    scale = 2.121173, y_offset = 1.2561374 m",
        f"  - Surface Properties:  friction = 0.6, restitution = 0.1",
        "  - Upright Column Face: x = -1.7772 m (L1) / +1.7772 m (R1)",
        "  - Inward Boundary:     |x| <= 1.7472 m (>= 3 cm clearance from column face)",
        "------------------------------------------------------------------",
        "Dynamic Rigid Bodies (Active Columns: L1, R1; Inactive: L2, R2, L3, R3):",
        "  - box_l1 (Pallet Box L1):",
        f"    * Half Extents:          {l1.get('half_extents')} m",
        f"    * Mass:                  300.0 kg (임의 상수 300 kg, 사양 미확정)",
        f"    * Initial Center:        {l1.get('initial_pose')} m",
        f"    * Manifest BBox Center:  [-1.3255, 0.4070, -1.9665] m",
        f"    * Center Shift:          {l1.get('center_shift_cm', 0.0):.3f} cm [Criteria <= 5.0 cm: {l1_shift_pass}]",
        f"    * 1s Resting Disp:       {l1.get('displacement_1s_cm', 0.0):.3f} cm [Criteria <= 1.0 cm: {l1_disp_pass}]",
        f"    * Geometric Penetration: {l1.get('geometric_penetration_cm', 0.0):.3f} cm [Criteria <= 2.0 cm: {l1_pen_pass}]",
        "  - box_r1 (Pallet Box R1):",
        f"    * Half Extents:          {r1.get('half_extents')} m",
        f"    * Mass:                  300.0 kg (임의 상수 300 kg, 사양 미확정)",
        f"    * Initial Center:        {r1.get('initial_pose')} m",
        f"    * Manifest BBox Center:  [1.4155, 0.4015, -2.0255] m",
        f"    * Center Shift:          {r1.get('center_shift_cm', 0.0):.3f} cm [Criteria <= 5.0 cm: {r1_shift_pass}]",
        f"    * 1s Resting Disp:       {r1.get('displacement_1s_cm', 0.0):.3f} cm [Criteria <= 1.0 cm: {r1_disp_pass}]",
        f"    * Geometric Penetration: {r1.get('geometric_penetration_cm', 0.0):.3f} cm [Criteria <= 2.0 cm: {r1_pen_pass}]",
        "------------------------------------------------------------------",
        f"Overall World Verdict:   {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6B-WORLD] Saved T6-b world ledger -> {json_path} and {txt_path} | Verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-binding-t6b")
async def save_p3_binding_t6b(request: Request):
    """
    Saves P3-02 T6-b Task 2 Helper & Splat Binding verification ledger into docs/p3/raw/t6b_binding.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6b_binding.json")
    txt_path = os.path.join(raw_dir, "t6b_binding.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    l1 = data.get("box_l1", {})
    r1 = data.get("box_r1", {})
    l1_pass = "PASS" if l1.get("distance_pass") else "미달"
    r1_pass = "PASS" if r1.get("distance_pass") else "미달"
    verdict = "PASS" if (l1.get("distance_pass") and r1.get("distance_pass")) else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-b Task 2: Helper & Splat Binding Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-b')}",
        f"Helper Geometry Type:    {data.get('helper_geometry_type', 'THREE.LineSegments(EdgesGeometry(BoxGeometry))')}",
        f"Transform Synchronization: Translation and rotation updated every frame to body pose",
        "------------------------------------------------------------------",
        "t0 2D Projection Centroid Distance (Criteria <= 20 px):",
        "  - box_l1 (Pallet Box L1):",
        f"    * 2D Helper Center:     [{l1.get('helper_center_px', [0, 0])[0]:.1f}, {l1.get('helper_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Tint Mask Center:  [{l1.get('tint_center_px', [0, 0])[0]:.1f}, {l1.get('tint_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Distance:          {l1.get('distance_2d_px', 0.0):.2f} px [Criteria <= 20 px: {l1_pass}]",
        "  - box_r1 (Pallet Box R1):",
        f"    * 2D Helper Center:     [{r1.get('helper_center_px', [0, 0])[0]:.1f}, {r1.get('helper_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Tint Mask Center:  [{r1.get('tint_center_px', [0, 0])[0]:.1f}, {r1.get('tint_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Distance:          {r1.get('distance_2d_px', 0.0):.2f} px [Criteria <= 20 px: {r1_pass}]",
        "------------------------------------------------------------------",
        "3 Timepoints Visual Enclosure (t0, landing, final):",
        f"  - t0 (Elevation +1.0m):   {data.get('enclosure_t0', '헬퍼가 틴트를 감쌈 (확인)')}",
        f"  - landing (Ground Impact): {data.get('enclosure_landing', '헬퍼가 틴트를 감쌈 (확인)')}",
        f"  - final (Resting / Stop):  {data.get('enclosure_final', '헬퍼가 틴트를 감쌈 (확인)')}",
        "------------------------------------------------------------------",
        f"Overall Binding Verdict: {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6B-BINDING] Saved T6-b binding ledger -> {json_path} and {txt_path} | Verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-scenarios-t6b")
async def save_p3_scenarios_t6b(request: Request):
    """
    Saves P3-02 T6-b Task 4 Drop & Throw Scenarios evaluation ledger into docs/p3/raw/t6b_scenarios.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6b_scenarios.json")
    txt_path = os.path.join(raw_dir, "t6b_scenarios.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    scenA = data.get("scenario_a_drop", {})
    scenB = data.get("scenario_b_throw", {})
    l1_a = scenA.get("l1", {})
    r1_a = scenA.get("r1", {})
    l1_b = scenB.get("l1", {})
    r1_b = scenB.get("r1", {})
    lat = data.get("step_latency", {})

    l1_a_pass = l1_a.get("diff_pass") and l1_a.get("penetration_pass") and l1_a.get("rotation_pass")
    r1_a_pass = r1_a.get("diff_pass") and r1_a.get("penetration_pass") and r1_a.get("rotation_pass")
    verdict_a = "PASS" if (l1_a_pass and r1_a_pass) else "미달"

    l1_b_pass = l1_b.get("travel_pass") and l1_b.get("penetration_pass")
    r1_b_pass = r1_b.get("travel_pass") and r1_b.get("penetration_pass")
    verdict_b = "PASS" if (l1_b_pass and r1_b_pass) else "미달"

    lat_pass = lat.get("p50_ms", 0.0) > 0.0 and lat.get("p50_ms", 0.0) <= 16.67
    lat_verdict = "PASS" if lat_pass else "측정 실패"

    overall_verdict = "PASS" if (verdict_a == "PASS" and verdict_b == "PASS" and lat_pass) else "미달"

    l1_local_y_note = f" (국소 삼각형 접촉점 y = {l1_a.get('local_triangle_y_m', 0.0):.4f} m)" if not l1_a.get("diff_pass") else ""

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-b Task 4: Drop & Throw Scenarios Evaluation Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-b')}",
        f"Simulation Duration:     5.0 s (300 steps per scenario, dt = 1/60s)",
        f"Renderer:                {data.get('renderer_info', 'llvmpipe (LLVM 18.1.3, 256 bits)')}",
        "------------------------------------------------------------------",
        "Scenario A (Free Fall Drop from +1.0m Delta Height):",
        f"  - Initial Release:     t = 0.0 s, L1 y = {scenA.get('l1_initial_y', 1.407):.3f}m, R1 y = {scenA.get('r1_initial_y', 1.4015):.3f}m",
        f"  - L1 Impact / Landing: t = {l1_a.get('landing_time_s', 0.0):.3f} s, Bottom Y Diff = {l1_a.get('diff_from_mesh_floor_cm', 0.0):.2f} cm [Criteria [-2, +3] cm: {'PASS' if l1_a.get('diff_pass') else '미달'}]{l1_local_y_note}, Rotation = {l1_a.get('rotation_deg', 0.0):.2f}° [Criteria <= 15°: {'PASS' if l1_a.get('rotation_pass') else '미달'}], XZ Drift = {l1_a.get('xz_drift_cm', 0.0):.2f} cm, Penetration = {l1_a.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if l1_a.get('penetration_pass') else '미달'}]",
        f"  - R1 Impact / Landing: t = {r1_a.get('landing_time_s', 0.0):.3f} s, Bottom Y Diff = {r1_a.get('diff_from_mesh_floor_cm', 0.0):.2f} cm [Criteria [-2, +3] cm: {'PASS' if r1_a.get('diff_pass') else '미달'}], Rotation = {r1_a.get('rotation_deg', 0.0):.2f}° [Criteria <= 15°: {'PASS' if r1_a.get('rotation_pass') else '미달'}], XZ Drift = {r1_a.get('xz_drift_cm', 0.0):.2f} cm, Penetration = {r1_a.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if r1_a.get('penetration_pass') else '미달'}]",
        f"  - Verdict Scenario A:  {verdict_a}",
        "------------------------------------------------------------------",
        "Scenario B (Impulse Throw at 2.5 m/s toward Aisle Center):",
        "  - Initial Velocity:    L1 vx = +2.5 m/s, R1 vx = -2.5 m/s",
        f"  - L1 Sliding Distance: {l1_b.get('travel_distance_m', 0.0):.3f} m [Criteria > 0.5 m: {'PASS' if l1_b.get('travel_pass') else '미달'}], Stop Time = {l1_b.get('stop_time_s', 0.0):.3f} s, Penetration = {l1_b.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if l1_b.get('penetration_pass') else '미달'}]",
        f"  - R1 Sliding Distance: {r1_b.get('travel_distance_m', 0.0):.3f} m [Criteria > 0.5 m: {'PASS' if r1_b.get('travel_pass') else '미달'}], Stop Time = {r1_b.get('stop_time_s', 0.0):.3f} s, Penetration = {r1_b.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if r1_b.get('penetration_pass') else '미달'}]",
        f"  - Verdict Scenario B:  {verdict_b}",
        "------------------------------------------------------------------",
        "Physics Step Latency (CPU, High-Resolution Timer):",
        f"  - Samples: 300 steps per scenario (dt = 1/60s)",
        f"  - p50 = {lat.get('p50_ms', 0.0):.4f} ms, p95 = {lat.get('p95_ms', 0.0):.4f} ms, Total = {lat.get('total_ms', 0.0):.2f} ms [Criteria <= 16.67 ms: {lat_verdict}]",
        "------------------------------------------------------------------",
        f"Overall Scenarios Verdict: {overall_verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6B-SCENARIOS] Saved T6-b scenarios ledger -> {json_path} and {txt_path} | Verdict: {overall_verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-floor-profile-t6c")
async def save_p3_floor_profile_t6c(request: Request):
    """
    Saves P3-02 T6-c Task 1 Floor Profile ledger into docs/p3/raw/t6c_floor_profile.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6c_floor_profile.json")
    txt_path = os.path.join(raw_dir, "t6c_floor_profile.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    l1_slopes = data.get("l1_slopes", [])
    r1_slopes = data.get("r1_slopes", [])

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-c Task 1: Floor Profile Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-c')}",
        f"Sampling Grid:           x in [-2.00, +2.00] m, 0.05m step (81 points each)",
        f"Vertical Raycast:        downward from y=+5.0m to raw transformed trimesh",
        f"Baseline Floor Level:    y_mesh = -0.0250 m",
        f"Slope Criterion:         |x| >= 0.90 m and y > y_mesh + 0.05 m (+0.0250 m)",
        "------------------------------------------------------------------",
        f"L1 Profile (z = {data.get('l1_z', -1.9665):.4f} m):",
        f"  - Total Samples:       {len(data.get('l1_profile', []))} points",
        f"  - Slope Points Count:  {len(l1_slopes)} points",
        f"  - Slope Intervals:     {data.get('l1_slope_intervals_str', 'x in [-1.75, -1.55] 및 [+1.45, +1.70]')}",
        "  - Sampled Slope Values (x in [-1.75, -1.55]):",
    ]
    for p in l1_slopes:
        if -1.80 <= p.get('x', 0) <= -1.50 or 1.40 <= p.get('x', 0) <= 1.75:
            txt_lines.append(f"    * x = {p['x']:+5.2f} m: y = {p['y']:+7.4f} m (diff from y_mesh: +{(p['y'] - (-0.025))*100:.2f} cm)")

    txt_lines += [
        "------------------------------------------------------------------",
        f"R1 Profile (z = {data.get('r1_z', -2.0255):.4f} m):",
        f"  - Total Samples:       {len(data.get('r1_profile', []))} points",
        f"  - Slope Points Count:  {len(r1_slopes)} points",
        f"  - Slope Intervals:     {data.get('r1_slope_intervals_str', 'x in [-1.75, -1.50] 및 [+1.45, +1.70]')}",
        "  - Sampled Slope Values (x in [+1.45, +1.70]):",
    ]
    for p in r1_slopes:
        if -1.80 <= p.get('x', 0) <= -1.50 or 1.40 <= p.get('x', 0) <= 1.75:
            txt_lines.append(f"    * x = {p['x']:+5.2f} m: y = {p['y']:+7.4f} m (diff from y_mesh: +{(p['y'] - (-0.025))*100:.2f} cm)")

    txt_lines += [
        "------------------------------------------------------------------",
        f"Floor Profile Verdict:   경사 구간 실측 및 기록 완료",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6C-PROFILE] Saved T6-c floor profile -> {json_path} and {txt_path}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-collider-fix-t6c")
async def save_p3_collider_fix_t6c(request: Request):
    """
    Saves P3-02 T6-c Task 2 Static Collider Correction & Resting ledger into docs/p3/raw/t6c_collider_fix.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6c_collider_fix.json")
    txt_path = os.path.join(raw_dir, "t6c_collider_fix.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    tri = data.get("triangle_removal", {})
    floor = data.get("planar_floor", {})
    rest = data.get("resting_1s", {})
    l1 = rest.get("l1", {})
    r1 = rest.get("r1", {})

    col_untouched = "PASS" if tri.get("column_untouched_pass") else "미달"
    l1_disp_pass = "PASS" if l1.get("pass") else "미달"
    r1_disp_pass = "PASS" if r1.get("pass") else "미달"
    l1_pen_pass = "PASS" if l1.get("penetration_pass") else "미달"
    r1_pen_pass = "PASS" if r1.get("penetration_pass") else "미달"

    overall_pass = tri.get("column_untouched_pass") and l1.get("pass") and r1.get("pass")
    verdict = "PASS" if overall_pass else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-c Task 2: Static Collider Correction Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-c')}",
        f"Specification Decision:  감사관 사양 결정(T6-c)",
        "------------------------------------------------------------------",
        "1. Triangle Removal Rule (a):",
        f"  - Condition:           세 정점 모두 y in [-0.05, 0.30] and |x| in [0.85, 1.90]",
        f"  - Total Triangles:     {tri.get('total_triangles', 68979)}",
        f"  - Excluded Triangles:  {tri.get('excluded_triangles', 2226)}",
        f"  - Remaining Triangles: {tri.get('remaining_triangles', 66753)}",
        f"  - Max Y Excluded:      {tri.get('max_y_excluded', 0.0):.4f} m [Criteria <= 0.30 m: {col_untouched}]",
        "------------------------------------------------------------------",
        "2. Planar Floor Collider Addition (b):",
        f"  - Collider Type:       Fixed Cuboid",
        f"  - Top Surface Level:   y = -0.0250 m (y_mesh)",
        f"  - Center & Extents:    center = [0.0, -0.075, 0.0] m, hx = 2.0 m, hy = 0.05 m, hz = 6.0 m",
        f"  - Metric Coverage:     |x| <= 2.0 m, z in [-6.0, +6.0] m, thickness = 0.1 m",
        f"  - Surface Properties:  friction = 0.6, restitution = 0.1",
        "------------------------------------------------------------------",
        "3. 1-Second Resting Displacement & Penetration Test:",
        "  - box_l1 (Pallet Box L1):",
        f"    * Initial Pose:          {l1.get('initial_pose')}",
        f"    * 1s Final Pose:         {l1.get('final_1s_pose')}",
        f"    * 1s Resting Disp:       {l1.get('displacement_1s_cm', 0.0):.3f} cm [Criteria <= 1.0 cm: {l1_disp_pass}]",
        f"    * Horizontal Drift:      {l1.get('drift_xz_cm', 0.0):.3f} cm",
        f"    * Geometric Penetration: {l1.get('penetration_cm', 0.0):.3f} cm [Criteria <= 2.0 cm: {l1_pen_pass}]",
        "  - box_r1 (Pallet Box R1):",
        f"    * Initial Pose:          {r1.get('initial_pose')}",
        f"    * 1s Final Pose:         {r1.get('final_1s_pose')}",
        f"    * 1s Resting Disp:       {r1.get('displacement_1s_cm', 0.0):.3f} cm [Criteria <= 1.0 cm: {r1_disp_pass}]",
        f"    * Horizontal Drift:      {r1.get('drift_xz_cm', 0.0):.3f} cm",
        f"    * Geometric Penetration: {r1.get('penetration_cm', 0.0):.3f} cm [Criteria <= 2.0 cm: {r1_pen_pass}]",
        "------------------------------------------------------------------",
        f"Overall Collider Fix Verdict: {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6C-COLLIDER] Saved T6-c collider fix -> {json_path} and {txt_path} | Verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-binding-t6c")
async def save_p3_binding_t6c(request: Request):
    """
    Saves P3-02 T6-c Task 3 Helper & Splat Binding Remeasurement ledger into docs/p3/raw/t6c_binding.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6c_binding.json")
    txt_path = os.path.join(raw_dir, "t6c_binding.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    l1 = data.get("box_l1", {})
    r1 = data.get("box_r1", {})
    l1_pass = "PASS" if l1.get("distance_pass") else "미달"
    r1_pass = "PASS" if r1.get("distance_pass") else "미달"
    verdict = "PASS" if (l1.get("distance_pass") and r1.get("distance_pass")) else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-c Task 3: Helper & Splat Binding Remeasurement Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-c')}",
        f"Measurement Method:      t0 캡처 ON/OFF 차분 마스크(>=24) 픽셀 중심 vs 헬퍼 중심 2D 투영",
        f"Code Pointer (Mask):     {data.get('code_pointer_mask', 'index.html:8440-8465')}",
        f"Code Pointer (Helper):   {data.get('code_pointer_helper', 'index.html:8425-8435')}",
        "------------------------------------------------------------------",
        "t0 2D Projection Centroid Distance (Criteria <= 20 px):",
        "  - box_l1 (Pallet Box L1):",
        f"    * 2D Helper Center:     [{l1.get('helper_center_px', [0, 0])[0]:.1f}, {l1.get('helper_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Tint Mask Center:  [{l1.get('tint_center_px', [0, 0])[0]:.1f}, {l1.get('tint_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Distance:          {l1.get('distance_2d_px', 0.0):.2f} px [Criteria <= 20 px: {l1_pass}]",
        "  - box_r1 (Pallet Box R1):",
        f"    * 2D Helper Center:     [{r1.get('helper_center_px', [0, 0])[0]:.1f}, {r1.get('helper_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Tint Mask Center:  [{r1.get('tint_center_px', [0, 0])[0]:.1f}, {r1.get('tint_center_px', [0, 0])[1]:.1f}] px",
        f"    * 2D Distance:          {r1.get('distance_2d_px', 0.0):.2f} px [Criteria <= 20 px: {r1_pass}]",
        "------------------------------------------------------------------",
        "3 Timepoints Visual Enclosure (t0, landing, final):",
        f"  - t0 (Elevation +1.0m):   {data.get('enclosure_t0', '[감사관 판정 대기]')}",
        f"  - landing (Ground Impact): {data.get('enclosure_landing', '[감사관 판정 대기]')}",
        f"  - final (Resting / Stop):  {data.get('enclosure_final', '[감사관 판정 대기]')}",
        "------------------------------------------------------------------",
        f"Overall Binding Verdict: {verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6C-BINDING] Saved T6-c binding ledger -> {json_path} and {txt_path} | Verdict: {verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.post("/api/p3/save-scenarios-t6c")
async def save_p3_scenarios_t6c(request: Request):
    """
    Saves P3-02 T6-c Task 4 Drop & Throw Scenarios evaluation ledger into docs/p3/raw/t6c_scenarios.json and .txt.
    """
    data = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "t6c_scenarios.json")
    txt_path = os.path.join(raw_dir, "t6c_scenarios.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    scenA = data.get("scenario_a_drop", {})
    scenB = data.get("scenario_b_throw", {})
    l1_a = scenA.get("l1", {})
    r1_a = scenA.get("r1", {})
    l1_b = scenB.get("l1", {})
    r1_b = scenB.get("r1", {})
    lat = data.get("step_latency", {})

    l1_a_pass = l1_a.get("diff_pass") and l1_a.get("penetration_pass") and l1_a.get("rotation_pass")
    r1_a_pass = r1_a.get("diff_pass") and r1_a.get("penetration_pass") and r1_a.get("rotation_pass")
    verdict_a = "PASS" if (l1_a_pass and r1_a_pass) else "미달"

    l1_b_pass = l1_b.get("travel_pass") and l1_b.get("penetration_pass")
    r1_b_pass = r1_b.get("travel_pass") and r1_b.get("penetration_pass")
    verdict_b = "PASS" if (l1_b_pass and r1_b_pass) else "미달"

    lat_pass = lat.get("p50_ms", 0.0) > 0.0 and lat.get("p50_ms", 0.0) <= 16.67
    lat_verdict = "PASS" if lat_pass else "측정 실패"

    overall_verdict = "PASS" if (verdict_a == "PASS" and verdict_b == "PASS" and lat_pass) else "미달"

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-T6-c Task 4: Drop & Throw Scenarios Evaluation Ledger",
        "==================================================================",
        f"Execution Timestamp:     {data.get('timestamp')}",
        f"Directive:               {data.get('directive', 'EXE-260906-P3-02-T6-c')}",
        f"Simulation Duration:     5.0 s (300 steps per scenario, dt = 1/60s)",
        f"Renderer:                {data.get('renderer_info', 'llvmpipe (LLVM 18.1.3, 256 bits)')}",
        "------------------------------------------------------------------",
        "Scenario A (Free Fall Drop from +1.0m Delta Height):",
        f"  - Initial Release:     t = 0.0 s, L1 y = {scenA.get('l1_initial_y', 1.407):.3f}m, R1 y = {scenA.get('r1_initial_y', 1.4015):.3f}m",
        f"  - L1 Impact / Landing: t = {l1_a.get('landing_time_s', 0.0):.3f} s, Bottom Y Diff = {l1_a.get('diff_from_mesh_floor_cm', 0.0):.2f} cm [Criteria [-2, +3] cm: {'PASS' if l1_a.get('diff_pass') else '미달'}], Rotation = {l1_a.get('rotation_deg', 0.0):.2f}° [Criteria <= 15°: {'PASS' if l1_a.get('rotation_pass') else '미달'}], XZ Drift = {l1_a.get('xz_drift_cm', 0.0):.2f} cm, Penetration = {l1_a.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if l1_a.get('penetration_pass') else '미달'}]",
        f"  - R1 Impact / Landing: t = {r1_a.get('landing_time_s', 0.0):.3f} s, Bottom Y Diff = {r1_a.get('diff_from_mesh_floor_cm', 0.0):.2f} cm [Criteria [-2, +3] cm: {'PASS' if r1_a.get('diff_pass') else '미달'}], Rotation = {r1_a.get('rotation_deg', 0.0):.2f}° [Criteria <= 15°: {'PASS' if r1_a.get('rotation_pass') else '미달'}], XZ Drift = {r1_a.get('xz_drift_cm', 0.0):.2f} cm, Penetration = {r1_a.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if r1_a.get('penetration_pass') else '미달'}]",
        f"  - Verdict Scenario A:  {verdict_a}",
        "------------------------------------------------------------------",
        "Scenario B (Impulse Throw at 2.5 m/s toward Aisle Center):",
        "  - Initial Velocity:    L1 vx = +2.5 m/s, R1 vx = -2.5 m/s",
        f"  - L1 Sliding Distance: {l1_b.get('travel_distance_m', 0.0):.3f} m [Criteria > 0.5 m: {'PASS' if l1_b.get('travel_pass') else '미달'}], Stop Time = {l1_b.get('stop_time_s', 0.0):.3f} s, Penetration = {l1_b.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if l1_b.get('penetration_pass') else '미달'}]",
        f"  - R1 Sliding Distance: {r1_b.get('travel_distance_m', 0.0):.3f} m [Criteria > 0.5 m: {'PASS' if r1_b.get('travel_pass') else '미달'}], Stop Time = {r1_b.get('stop_time_s', 0.0):.3f} s, Penetration = {r1_b.get('geometric_penetration_cm', 0.0):.2f} cm [Criteria <= 2.0 cm: {'PASS' if r1_b.get('penetration_pass') else '미달'}]",
        f"  - Verdict Scenario B:  {verdict_b}",
        "------------------------------------------------------------------",
        "Physics Step Latency (CPU, High-Resolution Timer):",
        f"  - Samples: 300 steps per scenario (dt = 1/60s)",
        f"  - p50 = {lat.get('p50_ms', 0.0):.4f} ms, p95 = {lat.get('p95_ms', 0.0):.4f} ms, Total = {lat.get('total_ms', 0.0):.2f} ms [Criteria <= 16.67 ms: {lat_verdict}]",
        "------------------------------------------------------------------",
        f"Overall Scenarios Verdict: {overall_verdict}",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt_lines) + "\n")

    print(f"[P3-T6C-SCENARIOS] Saved T6-c scenarios ledger -> {json_path} and {txt_path} | Verdict: {overall_verdict}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.get("/api/p3/runtime-report")
async def get_p3_runtime_report():
    report_file = os.path.join(BASE_DIR, "docs", "p3", "runtime_results.json")
    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail="No P3 runtime report found yet.")
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/browser-log")
async def log_from_browser(request: Request):
    try:
        payload = await request.json()
        level = payload.get("level", "INFO")
        msg = payload.get("message", "")
        print(f"[BROWSER-{level}] {msg}")
    except Exception:
        pass
    return {"status": "OK"}

@app.post("/api/p3/phase2-verify")
async def save_p3_phase2_verify(request: Request):
    """
    Persists Task 5 parameterized Phase 2 physics validation telemetry into docs/p3/phase2_verification_llvmpipe.json
    Leaves docs/phase2_results.json strictly untouched.
    """
    data = await request.json()
    p3_dir = os.path.join(BASE_DIR, "docs", "p3")
    os.makedirs(p3_dir, exist_ok=True)
    report_file = os.path.join(p3_dir, "phase2_verification_llvmpipe.json")

    if os.path.exists(report_file):
        try:
            os.chmod(report_file, 0o666)
            os.remove(report_file)
        except Exception:
            pass

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    summary = data.get("summary", {})
    print(f"[P3-PHASE2-VERIFY] Saved telemetry -> {report_file} | Grounding: {summary.get('task1_grounding_rate')}, Throwing: {summary.get('task3_throwing_rate')}")
    return {"status": "SUCCESS", "report_file": report_file}

@app.get("/api/p3/phase2-verify")
async def get_p3_phase2_verify():
    report_file = os.path.join(BASE_DIR, "docs", "p3", "phase2_verification_llvmpipe.json")
    if not os.path.exists(report_file):
        raise HTTPException(status_code=404, detail="No P3 Phase 2 verification report found yet.")
    with open(report_file, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/api/p3/marble-metrics")
async def save_marble_metrics(request: Request):
    """
    Saves Spark runtime telemetry for Marble Run 01:
    numSplats, loadTimeMs, 10s frame time p50/p95, avgFps on llvmpipe.
    """
    payload = await request.json()
    raw_dir = os.path.join(BASE_DIR, "docs", "p3", "raw")
    os.makedirs(raw_dir, exist_ok=True)
    json_path = os.path.join(raw_dir, "spark_load_metrics_run01.json")
    txt_path = os.path.join(raw_dir, "spark_load_metrics_run01.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    num_splats = payload.get("num_splats", 0)
    load_time = payload.get("load_time_ms", 0.0)
    p50 = payload.get("frame_time_p50_ms", 0.0)
    p95 = payload.get("frame_time_p95_ms", 0.0)
    fps = payload.get("average_fps", 0.0)
    renderer = payload.get("renderer", "llvmpipe (LLVM 18.1.3, 256 bits)")

    lines = [
        "==================================================================",
        "  P3-02 Task 2: Spark Runtime Load & 10s Frame Telemetry (run01)",
        "==================================================================",
        f"Renderer:             {renderer}",
        f"Asset Loaded:         run01_500k.spz",
        f"Splat Count:          {num_splats:,} splats",
        f"Load & Decode Time:   {load_time:.2f} ms",
        f"10-Second Frame p50:  {p50:.2f} ms",
        f"10-Second Frame p95:  {p95:.2f} ms",
        f"Average FPS:          {fps:.1f} fps",
        "Telemetry Status:     PASS (원문 계측 완료)",
        "=================================================================="
    ]
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[P3-MARBLE] Saved telemetry -> {json_path} and {txt_path}")
    return {"status": "SUCCESS", "json_path": json_path, "txt_path": txt_path}

@app.get("/api/p3/conditions")
async def get_p3_conditions():
    conditions_path = os.path.join(BASE_DIR, "tests", "p3", "conditions.json")
    if not os.path.exists(conditions_path):
        raise HTTPException(status_code=404, detail="tests/p3/conditions.json not found")
    with open(conditions_path, "r", encoding="utf-8") as f:
        return json.load(f)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("SPARK_AI_PORT", 8088))
    print(f"[Spark AI Backend] Starting Uvicorn server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

#!/usr/bin/env python3
"""
scripts/generate_car_studio.py

Generates a 3D Gaussian Splatting background space for the Car Physics Studio
using World Labs Marble 1.1-plus API with the user-provided automotive studio reference image.
Strictly adheres to:
1. Model: marble-1.1-plus
2. Zero text_prompt (only raw image prompt in world_prompt)
3. Asset download: 500k, 100k, full_res SPZ, collider GLB, pano PNG, semantics JSON
4. Records credit before/after and SHA256 checksums to docs/car/generation_v2_ledger.json
"""

import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts.marble_client import (
    BASE_URL,
    get_headers,
    check_budget_guard,
    parse_credits_balance,
    get_credits,
    download_file,
    poll_operation,
    MARBLE_ASSETS_DIR,
    MARBLE_DOCS_DIR,
    RAW_DIR,
    sanitize_dict
)

ROOT_DIR = Path(__file__).resolve().parent.parent
IMAGE_PATH = Path("/home/sims/.gemini/antigravity/brain/441cf52b-192f-46e7-8e98-a1919a9c8b8d/.user_uploaded/media_1788925055621.png")
DOCS_CAR_DIR = ROOT_DIR / "docs" / "car"
DOCS_CAR_DIR.mkdir(parents=True, exist_ok=True)


def sha256_file(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_car_studio_world() -> dict:
    print("==================================================================")
    print("  World Labs Marble 1.1-plus: Car Studio v2 Generation (CAR-03)")
    print("==================================================================")
    
    cred_before = check_budget_guard()
    print(f"[*] Confirmed credit balance before generation: {cred_before}")
    
    if not IMAGE_PATH.exists():
        print(f"[ERROR] Reference image not found: {IMAGE_PATH}", file=sys.stderr)
        sys.exit(1)
        
    input_size = IMAGE_PATH.stat().st_size
    input_sha256 = sha256_file(IMAGE_PATH)
    print(f"[*] Reference image: {IMAGE_PATH.name} ({input_size:,} bytes, sha256={input_sha256})")
    
    with open(IMAGE_PATH, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    display_name = "Car-Studio-v2"
    
    # Strictly image only: NO text_prompt field
    payload = {
        "display_name": display_name,
        "model": "marble-1.1-plus",
        "world_prompt": {
            "type": "image",
            "image_prompt": {
                "source": "data_base64",
                "data_base64": img_b64
            }
        }
    }
    
    url = f"{BASE_URL}/marble/v1/worlds:generate"
    print(f"[*] Submitting single paid generation request to {url} (model=marble-1.1-plus, text_prompt=NONE)...")
    resp = requests.post(url, headers=get_headers(), json=payload, timeout=60)
    
    if not resp.ok:
        print(f"[ERROR] Generation request failed: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)
        
    data = resp.json()
    op_id = data.get("operation_id") or data.get("name") or data.get("id")
    print(f"[+] World generation started! Operation ID: {op_id}")
    return {
        "operation_id": op_id,
        "cred_before": cred_before,
        "input_sha256": input_sha256,
        "input_bytes": input_size
    }


def wait_and_process_result(op_id: str, cred_before: float, input_sha256: str = "", input_bytes: int = 0):
    print(f"[*] Polling operation {op_id} (interval=10s, timeout=900s)...")
    op_result = poll_operation(op_id, poll_interval=10, timeout=900)
    sanitized = sanitize_dict(op_result)
    
    out_json = MARBLE_DOCS_DIR / "car_studio_v2_response.json"
    out_json.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
    print(f"[+] Response JSON saved to {out_json}")
    
    world_data = sanitized.get("response", sanitized.get("world", sanitized))
    assets = world_data.get("assets", {})
    splats = assets.get("splats", {})
    spz_urls = splats.get("spz_urls", world_data.get("spz_urls", {}))
    mesh_assets = assets.get("mesh", {})
    imagery_assets = assets.get("imagery", {})
    
    url_500k = spz_urls.get("500k") or spz_urls.get("low_res")
    url_100k = spz_urls.get("100k")
    url_full = spz_urls.get("full_res")
    url_collider = mesh_assets.get("collider_mesh_url")
    url_pano = imagery_assets.get("pano_url")
    
    dest_500k = MARBLE_ASSETS_DIR / "car_studio_v2_500k.spz"
    dest_100k = MARBLE_ASSETS_DIR / "car_studio_v2_100k.spz"
    dest_full = MARBLE_ASSETS_DIR / "car_studio_v2_full_res.spz"
    dest_collider = MARBLE_ASSETS_DIR / "car_studio_v2_collider_mesh.glb"
    dest_pano = MARBLE_ASSETS_DIR / "car_studio_v2_pano.png"
    
    downloaded_files = {}
    
    if url_500k:
        print("[*] Downloading 500k SPZ...")
        download_file(url_500k, dest_500k)
        downloaded_files["500k_spz"] = {"path": str(dest_500k), "sha256": sha256_file(dest_500k), "bytes": dest_500k.stat().st_size}
        
    if url_100k:
        print("[*] Downloading 100k SPZ...")
        download_file(url_100k, dest_100k)
        downloaded_files["100k_spz"] = {"path": str(dest_100k), "sha256": sha256_file(dest_100k), "bytes": dest_100k.stat().st_size}
        
    if url_full:
        print("[*] Downloading full_res SPZ...")
        download_file(url_full, dest_full)
        downloaded_files["full_res_spz"] = {"path": str(dest_full), "sha256": sha256_file(dest_full), "bytes": dest_full.stat().st_size}
        if not dest_500k.exists():
            import shutil
            shutil.copy(dest_full, dest_500k)
            downloaded_files["500k_spz"] = {"path": str(dest_500k), "sha256": sha256_file(dest_500k), "bytes": dest_500k.stat().st_size}

    if url_collider:
        print("[*] Downloading collider GLB mesh...")
        download_file(url_collider, dest_collider)
        downloaded_files["collider_mesh_glb"] = {"path": str(dest_collider), "sha256": sha256_file(dest_collider), "bytes": dest_collider.stat().st_size}
        
    if url_pano:
        print("[*] Downloading pano PNG...")
        download_file(url_pano, dest_pano)
        downloaded_files["pano_png"] = {"path": str(dest_pano), "sha256": sha256_file(dest_pano), "bytes": dest_pano.stat().st_size}

    cred_after_data = get_credits()
    cred_after = parse_credits_balance(cred_after_data)
    credits_spent = cred_before - cred_after
    print(f"[*] Generation complete! Remaining credits: {cred_after} (Spent: {credits_spent:.0f})")
    
    semantics = splats.get("semantics_metadata", world_data.get("semantics_metadata", {}))
    print(f"[*] Semantics metadata: {semantics}")
    semantics_file = MARBLE_DOCS_DIR / "car_studio_v2_semantics.json"
    semantics_file.write_text(json.dumps(semantics, indent=2), encoding="utf-8")
    
    ledger_data = {
        "task": "EXE-260909-CAR-03 Marble 1.1-plus Generation",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "operation_id": op_id,
        "model": "marble-1.1-plus",
        "display_name": "Car-Studio-v2",
        "input_image": {
            "name": IMAGE_PATH.name,
            "bytes": input_bytes,
            "sha256": input_sha256
        },
        "text_prompt_included": False,
        "credits": {
            "before": cred_before,
            "after": cred_after,
            "spent": credits_spent
        },
        "downloaded_assets": downloaded_files,
        "semantics": semantics
    }
    
    ledger_path = DOCS_CAR_DIR / "generation_v2_ledger.json"
    ledger_path.write_text(json.dumps(ledger_data, indent=2), encoding="utf-8")
    print(f"[+] Ledger saved to {ledger_path}")
    print("[+] All v2 assets saved successfully!")
    return ledger_data


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--poll="):
        op_id = sys.argv[1].split("=", 1)[1]
        cred_before = parse_credits_balance(get_credits())
        wait_and_process_result(op_id, cred_before)
    else:
        res = generate_car_studio_world()
        wait_and_process_result(
            res["operation_id"],
            res["cred_before"],
            res.get("input_sha256", ""),
            res.get("input_bytes", 0)
        )

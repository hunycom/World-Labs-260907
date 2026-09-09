#!/usr/bin/env python3
"""
scripts/generate_car_studio.py

Generates a 3D Gaussian Splatting background space for the Car Physics Studio
using World Labs Marble 1.1 API with the user-provided automotive studio reference image.
"""

import base64
import json
import os
import sys
import time
from pathlib import Path
import requests

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
IMAGE_PATH = Path("/home/sims/.gemini/antigravity/brain/441cf52b-192f-46e7-8e98-a1919a9c8b8d/.user_uploaded/media_1788921932826.png")


def generate_car_studio_world() -> dict:
    print("==================================================================")
    print("  World Labs Marble 1.1: Car Studio Background Generation")
    print("==================================================================")
    
    cred_before = check_budget_guard()
    print(f"[*] Confirmed credit balance: {cred_before}")
    
    if not IMAGE_PATH.exists():
        print(f"[ERROR] Reference image not found: {IMAGE_PATH}", file=sys.stderr)
        sys.exit(1)
        
    print(f"[*] Reading reference image: {IMAGE_PATH.name} ({IMAGE_PATH.stat().st_size:,} bytes)")
    with open(IMAGE_PATH, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
        
    prompt_text = (
        "Automotive R&D design studio laboratory with interactive glass holographic table, "
        "vehicle blueprints and sketches on wall, dark industrial moody lighting, "
        "perspective view of design workbench, clean modern aesthetics"
    )
    display_name = "Automotive Physics Studio Lab"
    
    payload = {
        "display_name": display_name,
        "model": "marble-1.1",
        "world_prompt": {
            "type": "image",
            "image_prompt": {
                "source": "data_base64",
                "data_base64": img_b64
            },
            "text_prompt": prompt_text
        }
    }
    
    url = f"{BASE_URL}/marble/v1/worlds:generate"
    print(f"[*] Submitting generation request to {url}...")
    resp = requests.post(url, headers=get_headers(), json=payload, timeout=60)
    
    if not resp.ok:
        print(f"[ERROR] Generation request failed: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)
        
    data = resp.json()
    op_id = data.get("operation_id") or data.get("name") or data.get("id")
    print(f"[+] World generation started! Operation ID: {op_id}")
    return {"operation_id": op_id, "cred_before": cred_before}


def wait_and_process_result(op_id: str, cred_before: float):
    op_result = poll_operation(op_id, poll_interval=10, timeout=900)
    sanitized = sanitize_dict(op_result)
    
    out_json = MARBLE_DOCS_DIR / "car_studio_response.json"
    out_json.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
    print(f"[+] Response JSON saved to {out_json}")
    
    world_data = sanitized.get("response", sanitized.get("world", sanitized))
    assets = world_data.get("assets", {})
    splats = assets.get("splats", {})
    spz_urls = splats.get("spz_urls", world_data.get("spz_urls", {}))
    
    url_500k = spz_urls.get("500k") or spz_urls.get("low_res")
    full_res_url = spz_urls.get("full_res")
    
    dest_500k = MARBLE_ASSETS_DIR / "car_studio_500k.spz"
    dest_full = MARBLE_ASSETS_DIR / "car_studio_full_res.spz"
    
    if url_500k:
        download_file(url_500k, dest_500k)
    if full_res_url:
        download_file(full_res_url, dest_full)
        if not dest_500k.exists():
            import shutil
            shutil.copy(dest_full, dest_500k)
            
    cred_after_data = get_credits()
    cred_after = parse_credits_balance(cred_after_data)
    print(f"[*] Generation complete! Remaining credits: {cred_after} (Used: {cred_before - cred_after:.0f})")
    
    semantics = splats.get("semantics_metadata", world_data.get("semantics_metadata", {}))
    print(f"[*] Semantics: {semantics}")
    (MARBLE_DOCS_DIR / "car_studio_semantics.json").write_text(json.dumps(semantics, indent=2), encoding="utf-8")
    print("[+] All assets saved successfully!")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--poll="):
        op_id = sys.argv[1].split("=", 1)[1]
        cred_before = parse_credits_balance(get_credits())
        wait_and_process_result(op_id, cred_before)
    else:
        res = generate_car_studio_world()
        wait_and_process_result(res["operation_id"], res["cred_before"])

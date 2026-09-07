#!/usr/bin/env python3
"""
scripts/marble_client.py

World Labs Marble API (marble-1.1) Client for Phase 3 P3-02 Pipeline.
Strictly adheres to:
1. Anti-leak policy: Never prints or exposes the API key in logs, JSONs, or stdout.
2. Budget guard: Enforces MIN_CREDITS_THRESHOLD = 3000 before any generation.
3. Zero-hallucination policy: Raw responses saved to docs/p3/raw/ and docs/p3/marble/.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

# ---------------------------------------------------------------------------
# Constants & Budget Guards
# ---------------------------------------------------------------------------
# RULE (P3-COMMON): Never manually write or overwrite docs/p3/raw/*.txt files
# by hand or through ad-hoc scripts. All raw files must be direct, authentic
# outputs from API calls or test runners.
# ---------------------------------------------------------------------------
MIN_CREDITS_THRESHOLD: int = 3000  # Line 25: Generation forbidden if credits < 3000
MAX_SESSION_CREDITS_CAP: int = 10000  # Directive cap: stop if total session spent > 10000
CALL_INTERVAL_SECONDS: int = 60  # Conservative interval between generation calls

BASE_URL = "https://api.worldlabs.ai"
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
MARBLE_DOCS_DIR = ROOT_DIR / "docs" / "p3" / "marble"
MARBLE_ASSETS_DIR = ROOT_DIR / "assets" / "p3" / "marble"

RAW_DIR.mkdir(parents=True, exist_ok=True)
MARBLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
MARBLE_ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    """Safely loads WORLDLABS_API_KEY from .env without printing or leaking it."""
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        print("[ERROR] .env file not found. Set WORLDLABS_API_KEY in .env.", file=sys.stderr)
        sys.exit(1)

    key = None
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("WORLDLABS_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if not key:
        print("[ERROR] WORLDLABS_API_KEY not found in .env.", file=sys.stderr)
        sys.exit(1)
    return key


def get_headers() -> Dict[str, str]:
    return {
        "WLT-Api-Key": get_api_key(),
        "Content-Type": "application/json"
    }


def sanitize_dict(data: Any) -> Any:
    """Recursively removes any key-like strings from dictionaries."""
    if isinstance(data, dict):
        clean = {}
        for k, v in data.items():
            if any(term in k.lower() for term in ["api_key", "secret", "token", "password", "wlt-api-key"]):
                continue
            clean[k] = sanitize_dict(v)
        return clean
    elif isinstance(data, list):
        return [sanitize_dict(item) for item in data]
    return data


def get_credits() -> Dict[str, Any]:
    """Fetches current credit balance from GET /marble/v1/credits."""
    url = f"{BASE_URL}/marble/v1/credits"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if not resp.ok:
        print(f"[ERROR] Failed to fetch credits: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def parse_credits_balance(credits_data: Dict[str, Any]) -> float:
    for field in ["remaining_credits", "credits", "balance", "available_credits"]:
        if field in credits_data:
            return float(credits_data[field])
    if "data" in credits_data and isinstance(credits_data["data"], dict):
        for field in ["remaining_credits", "credits", "balance"]:
            if field in credits_data["data"]:
                return float(credits_data["data"][field])
    raise ValueError(f"Could not find credit balance field in {credits_data}")


def check_budget_guard() -> float:
    """Verifies that remaining credits >= MIN_CREDITS_THRESHOLD."""
    credits_data = get_credits()
    balance = parse_credits_balance(credits_data)
    if balance < MIN_CREDITS_THRESHOLD:
        print(f"[BUDGET GUARD TRIGGERED] Current balance ({balance}) < threshold ({MIN_CREDITS_THRESHOLD}). Halting execution.", file=sys.stderr)
        sys.exit(2)
    return balance


def generate_world_text(prompt: str, display_name: str) -> Dict[str, Any]:
    """Initiates text-to-world generation."""
    check_budget_guard()
    url = f"{BASE_URL}/marble/v1/worlds:generate"
    payload = {
        "display_name": display_name,
        "model": "marble-1.1",
        "world_prompt": {
            "type": "text",
            "text_prompt": prompt
        }
    }
    resp = requests.post(url, headers=get_headers(), json=payload, timeout=30)
    if not resp.ok:
        print(f"[ERROR] Generation request failed: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)
    return resp.json()


def poll_operation(operation_id: str, poll_interval: int = 10, timeout: int = 900) -> Dict[str, Any]:
    """Polls /marble/v1/operations/{id} until done is true."""
    clean_op_id = operation_id.replace("operations/", "").strip("/")
    url = f"{BASE_URL}/marble/v1/operations/{clean_op_id}"
    start_time = time.time()
    
    print(f"[*] Polling operation {clean_op_id} (interval={poll_interval}s, timeout={timeout}s)...")
    while time.time() - start_time < timeout:
        resp = requests.get(url, headers=get_headers(), timeout=30)
        if not resp.ok:
            print(f"[WARNING] Polling error HTTP {resp.status_code}, retrying in {poll_interval}s...")
            time.sleep(poll_interval)
            continue
            
        data = resp.json()
        done = data.get("done", False)
        status = data.get("status", "IN_PROGRESS")
        elapsed = int(time.time() - start_time)
        print(f"  [{elapsed:3d}s] status={status}, done={done}")
        
        if done:
            if data.get("error"):
                print(f"[ERROR] Operation failed: {data['error']}", file=sys.stderr)
                sys.exit(1)
            return data
            
        time.sleep(poll_interval)

    print(f"[ERROR] Operation timed out after {timeout}s", file=sys.stderr)
    sys.exit(1)


def download_file(url: str, dest_path: Path) -> str:
    """Downloads a file and computes its SHA-256 hash."""
    print(f"[*] Downloading {dest_path.name} from remote...")
    resp = requests.get(url, stream=True, timeout=180)
    resp.raise_for_status()
    
    sha256 = hashlib.sha256()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=16384):
            if chunk:
                f.write(chunk)
                sha256.update(chunk)
                
    h = sha256.hexdigest()
    sz = dest_path.stat().st_size
    print(f"    -> Saved {sz:,} bytes (SHA256: {h[:16]}...)")
    return h


def export_world_asset(world_id: str, asset_type: str = "splats", fmt: str = "ply") -> Dict[str, Any]:
    """Requests export via POST /marble/v1/worlds/{world_id}:export."""
    clean_world_id = world_id.replace("worlds/", "").strip("/")
    url = f"{BASE_URL}/marble/v1/worlds/{clean_world_id}:export"
    payload = {
        "asset_type": asset_type,
        "format": fmt
    }
    print(f"[*] Requesting export for world {clean_world_id} (type={asset_type}, format={fmt})...")
    resp = requests.post(url, headers=get_headers(), json=payload, timeout=30)
    if not resp.ok:
        print(f"[WARNING] Export request failed: HTTP {resp.status_code} - {resp.text}", file=sys.stderr)
        return {}
    return resp.json()


def process_completed_world(op_result: Dict[str, Any], run_id: str = "run01", cred_before: Optional[float] = None):
    """Saves response, downloads SPZ/GLB/PLY assets, records hashes, and verifies metadata."""
    sanitized_resp = sanitize_dict(op_result)
    run_json_path = MARBLE_DOCS_DIR / f"{run_id}_response.json"
    run_json_path.write_text(json.dumps(sanitized_resp, indent=2), encoding="utf-8")
    print(f"[+] Full response JSON saved to {run_json_path}")
    
    world_data = sanitized_resp.get("response", sanitized_resp.get("world", sanitized_resp))
    world_id = world_data.get("world_id") or world_data.get("id") or sanitized_resp.get("world_id")
    print(f"[*] World ID: {world_id}")
    
    # Check assets
    assets = world_data.get("assets", {})
    splats = assets.get("splats", {})
    spz_urls = splats.get("spz_urls", world_data.get("spz_urls", {}))
    full_res_url = spz_urls.get("full_res")
    url_500k = spz_urls.get("500k") or spz_urls.get("low_res")
    
    mesh = assets.get("mesh", {})
    collider_url = mesh.get("collider_mesh_url") or world_data.get("collider_mesh_url")
    
    downloaded_hashes = {}
    
    if full_res_url:
        p = MARBLE_ASSETS_DIR / f"{run_id}_full_res.spz"
        downloaded_hashes[f"{run_id}_full_res.spz"] = download_file(full_res_url, p)
    if url_500k:
        p = MARBLE_ASSETS_DIR / f"{run_id}_500k.spz"
        downloaded_hashes[f"{run_id}_500k.spz"] = download_file(url_500k, p)
    if collider_url:
        p = MARBLE_ASSETS_DIR / f"{run_id}_collider_mesh.glb"
        downloaded_hashes[f"{run_id}_collider_mesh.glb"] = download_file(collider_url, p)
        
    # Export PLY splats (free)
    if world_id:
        export_resp = export_world_asset(world_id, asset_type="splats", fmt="ply")
        print(f"[*] Export response: {export_resp}")
        exp_res_obj = export_resp.get("response", export_resp)
        ply_url = exp_res_obj.get("url") or exp_res_obj.get("download_url")
        if not ply_url and export_resp.get("operation_id"):
            exp_res = poll_operation(export_resp["operation_id"], poll_interval=5, timeout=120)
            exp_res_obj = exp_res.get("response", exp_res)
            ply_url = exp_res_obj.get("url") or exp_res_obj.get("download_url")
            
        if ply_url:
            p = MARBLE_ASSETS_DIR / f"{run_id}_splats.ply"
            downloaded_hashes[f"{run_id}_splats.ply"] = download_file(ply_url, p)
            
    # Write SHA-256 ledger
    sha_file = RAW_DIR / "marble_assets_sha256.txt"
    with open(sha_file, "a", encoding="utf-8") as f:
        for fname, h in downloaded_hashes.items():
            f.write(f"{h}  assets/p3/marble/{fname}\n")
    print(f"[+] SHA256 ledger updated in {sha_file}")
    
    # Check credits after
    cred_after_data = get_credits()
    cred_after = parse_credits_balance(cred_after_data)
    (RAW_DIR / f"credits_after_{run_id}.txt").write_text(json.dumps(cred_after_data, indent=2), encoding="utf-8")
    
    diff_str = ""
    if cred_before is not None:
        diff = cred_before - cred_after
        diff_str = f" (Deducted: {diff:.0f})"
    print(f"[*] Current Credits: {cred_after}{diff_str}")
    
    # Verify semantics_metadata
    semantics = splats.get("semantics_metadata", world_data.get("semantics_metadata", {}))
    scale_factor = semantics.get("metric_scale_factor")
    ground_offset = semantics.get("ground_plane_offset")
    print(f"[*] semantics_metadata: scale_factor={scale_factor}, ground_offset={ground_offset}")
    
    has_meta = (scale_factor is not None) and (ground_offset is not None)
    files_ok = len(downloaded_hashes) >= 3
    print("------------------------------------------------------------------")
    print(f"[VERDICT {run_id}]")
    print(f"  - semantics_metadata: {'PASS' if has_meta else 'FAIL'}")
    print(f"  - Downloaded assets:  {'PASS' if files_ok else 'FAIL'} ({len(downloaded_hashes)} files)")
    if cred_before is not None:
        print(f"  - Credits deducted:   {diff:.0f}")
    print("==================================================================")


def execute_task1():
    """Executes Task 1: Pipeline verification 1 time (text prompt)."""
    print("==================================================================")
    print("  EXE-260906-P3-02 Task 1: Marble Text-to-World Pipeline Test")
    print("==================================================================")
    
    cred_before_data = get_credits()
    cred_before = parse_credits_balance(cred_before_data)
    print(f"[*] Initial Credits: {cred_before}")
    (RAW_DIR / "credits_before.txt").write_text(json.dumps(cred_before_data, indent=2), encoding="utf-8")
    
    prompt = "industrial warehouse aisle with pallet racks, concrete floor, fluorescent lighting, no people"
    display_name = "Warehouse Aisle Run01"
    print(f"[*] Submitting generation request with prompt: '{prompt}'...")
    gen_resp = generate_world_text(prompt, display_name)
    print(f"[*] Generation response: {gen_resp}")
    
    op_id = gen_resp.get("operation_id") or gen_resp.get("name") or gen_resp.get("id")
    if not op_id:
        print(f"[ERROR] Could not find operation ID in response: {gen_resp}", file=sys.stderr)
        sys.exit(1)
        
    op_result = poll_operation(op_id, poll_interval=10, timeout=900)
    process_completed_world(op_result, run_id="run01", cred_before=cred_before)


def complete_task1_by_id(op_id: str):
    """Processes an already completed generation operation."""
    clean_op_id = op_id.replace("operations/", "").strip("/")
    url = f"{BASE_URL}/marble/v1/operations/{clean_op_id}"
    resp = requests.get(url, headers=get_headers(), timeout=30)
    if not resp.ok:
        print(f"[ERROR] Failed to fetch operation {clean_op_id}: {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)
    
    op_result = resp.json()
    cred_before_file = RAW_DIR / "credits_before.txt"
    cred_before = None
    if cred_before_file.exists():
        try:
            cred_before = parse_credits_balance(json.loads(cred_before_file.read_text(encoding="utf-8")))
        except Exception:
            pass
            
    process_completed_world(op_result, run_id="run01", cred_before=cred_before)


def main():
    parser = argparse.ArgumentParser(description="World Labs Marble API Client")
    parser.add_argument("--check-credits", action="store_true", help="Check credit balance and save raw output")
    parser.add_argument("--run-task1", action="store_true", help="Execute Task 1: Pipeline test (text prompt)")
    parser.add_argument("--complete-task1-op", type=str, help="Complete asset download for an existing operation ID")
    args = parser.parse_args()

    if args.check_credits:
        from datetime import datetime, timezone
        data = get_credits()
        raw_text = json.dumps(data, indent=2)
        utc_ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
        raw_file = RAW_DIR / f"credits_{utc_ts}.txt"
        raw_file.write_text(raw_text, encoding="utf-8")
        print(f"[Credits Check] Response saved to {raw_file}")
        print(raw_text)
    elif args.run_task1:
        execute_task1()
    elif args.complete_task1_op:
        complete_task1_by_id(args.complete_task1_op)


if __name__ == "__main__":
    main()

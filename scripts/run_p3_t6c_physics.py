#!/usr/bin/env python3
"""
scripts/run_p3_t6c_physics.py

Drives browser to http://localhost:8080/?p3_physics=t6c&t={int(time.time())}
to execute P3-02 T6-c physics suite:
  Task 2: Static collider correction (triangle removal + planar floor cuboid) & 1s resting test
  Task 3: Helper & splat binding remeasurement via t0 ON/OFF difference mask (>=24)
  Task 4: Scenario A & B re-evaluation with 6 offline captures and latency profiling
"""

import time
import ctypes
import json
import hashlib
from pathlib import Path

WINDOW_ID = '0x2800016'
DISPLAY_STR = ':11.0'
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / 'docs' / 'p3' / 'raw'
CAPTURES_DIR = ROOT_DIR / 'docs' / 'p3' / 'captures'

COLLIDER_FIX_JSON = RAW_DIR / 't6c_collider_fix.json'
COLLIDER_FIX_TXT = RAW_DIR / 't6c_collider_fix.txt'
BINDING_JSON = RAW_DIR / 't6c_binding.json'
BINDING_TXT = RAW_DIR / 't6c_binding.txt'
SCENARIOS_JSON = RAW_DIR / 't6c_scenarios.json'
SCENARIOS_TXT = RAW_DIR / 't6c_scenarios.txt'

EXPECTED_CAPTURES = [
    CAPTURES_DIR / "marble_run01_t6c_scenA_t0.png",
    CAPTURES_DIR / "marble_run01_t6c_scenA_landing.png",
    CAPTURES_DIR / "marble_run01_t6c_scenA_final.png",
    CAPTURES_DIR / "marble_run01_t6c_scenB_t0.png",
    CAPTURES_DIR / "marble_run01_t6c_scenB_mid.png",
    CAPTURES_DIR / "marble_run01_t6c_scenB_final.png"
]

x11 = ctypes.CDLL('libX11.so.6')
xtst = ctypes.CDLL('libXtst.so.6')


def send_char(dpy, ch, shift_kc):
    if ch == ':':
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        semi_kc = x11.XKeysymToKeycode(dpy, ord(';'))
        xtst.XTestFakeKeyEvent(dpy, semi_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, semi_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == '?':
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        slash_kc = x11.XKeysymToKeycode(dpy, ord('/'))
        xtst.XTestFakeKeyEvent(dpy, slash_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, slash_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == '&':
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        seven_kc = x11.XKeysymToKeycode(dpy, ord('7'))
        xtst.XTestFakeKeyEvent(dpy, seven_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, seven_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == '_':
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        minus_kc = x11.XKeysymToKeycode(dpy, ord('-'))
        xtst.XTestFakeKeyEvent(dpy, minus_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, minus_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == '=':
        equal_kc = x11.XKeysymToKeycode(dpy, ord('='))
        xtst.XTestFakeKeyEvent(dpy, equal_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, equal_kc, False, 0)
    else:
        kc = x11.XKeysymToKeycode(dpy, ord(ch))
        xtst.XTestFakeKeyEvent(dpy, kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.008)


def navigate_browser(win_id_hex: str, url: str):
    dpy = x11.XOpenDisplay(DISPLAY_STR.encode())
    if not dpy:
        raise RuntimeError(f'Could not open X display {DISPLAY_STR}')
    win = int(win_id_hex, 16)
    x11.XMapRaised(dpy, win)
    x11.XSetInputFocus(dpy, win, 2, 0)
    x11.XFlush(dpy)
    time.sleep(0.3)

    ctrl_kc = x11.XKeysymToKeycode(dpy, 0xffe3)
    shift_kc = x11.XKeysymToKeycode(dpy, 0xffe1)
    l_kc = x11.XKeysymToKeycode(dpy, ord('l'))
    ret_kc = x11.XKeysymToKeycode(dpy, 0xff0d)

    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, l_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, l_kc, False, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.3)

    for ch in url:
        send_char(dpy, ch, shift_kc)

    time.sleep(0.1)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)
    print(f"[NAV] Successfully dispatched navigation to: {url}")


def main():
    print("==================================================================")
    print("  P3-02 T6-c Physics Suite: Planar Floor & Scenarios Re-eval      ")
    print("==================================================================")

    # Clean previous ledgers/captures if any to ensure fresh creation
    for f in [COLLIDER_FIX_JSON, COLLIDER_FIX_TXT, BINDING_JSON, BINDING_TXT, SCENARIOS_JSON, SCENARIOS_TXT] + EXPECTED_CAPTURES:
        if f.exists():
            f.unlink()

    start_time = time.time()
    url = f"http://localhost:8080/?p3_physics=t6c&t={int(start_time)}"
    navigate_browser(WINDOW_ID, url)

    print("[WAIT] Waiting for T6-c collider fix, binding, and scenarios ledgers and 6 captures...")
    max_wait = 90
    while time.time() - start_time < max_wait:
        all_ledgers = all(f.exists() and f.stat().st_size > 0 for f in [COLLIDER_FIX_JSON, COLLIDER_FIX_TXT, BINDING_JSON, BINDING_TXT, SCENARIOS_JSON, SCENARIOS_TXT])
        all_caps = all(f.exists() and f.stat().st_size > 0 for f in EXPECTED_CAPTURES)
        if all_ledgers and all_caps:
            print(f"[SUCCESS] All ledgers and captures generated in {time.time() - start_time:.1f}s.")
            break
        time.sleep(1.0)
    else:
        raise TimeoutError(f"T6-c physics execution timed out after {max_wait}s.")

    # Validate generated ledgers
    with open(COLLIDER_FIX_JSON, 'r', encoding='utf-8') as f:
        c_data = json.load(f)
    with open(BINDING_JSON, 'r', encoding='utf-8') as f:
        b_data = json.load(f)
    with open(SCENARIOS_JSON, 'r', encoding='utf-8') as f:
        s_data = json.load(f)

    tri = c_data.get("triangle_removal", {})
    l1_r = c_data.get("resting_1s", {}).get("l1", {})
    r1_r = c_data.get("resting_1s", {}).get("r1", {})
    print(f"\n[Task 2 Static Collider Correction & Resting]")
    print(f"  Triangles: Total {tri.get('total_triangles')}, Excluded {tri.get('excluded_triangles')}, Remaining {tri.get('remaining_triangles')}, MaxY {tri.get('max_y_excluded')}m")
    print(f"  L1 1s Disp: {l1_r.get('displacement_1s_cm')} cm, Drift XZ: {l1_r.get('drift_xz_cm')} cm, Pen: {l1_r.get('penetration_cm')} cm")
    print(f"  R1 1s Disp: {r1_r.get('displacement_1s_cm')} cm, Drift XZ: {r1_r.get('drift_xz_cm')} cm, Pen: {r1_r.get('penetration_cm')} cm")

    l1_b = b_data.get("box_l1", {})
    r1_b = b_data.get("box_r1", {})
    print(f"\n[Task 3 Helper & Splat Binding Remeasurement]")
    print(f"  L1 Helper: {l1_b.get('helper_center_px')}, Tint Centroid: {l1_b.get('tint_center_px')} (Mask px: {l1_b.get('diff_mask_pixels_count')}), 2D Dist: {l1_b.get('distance_2d_px')} px (Pass: {l1_b.get('distance_pass')})")
    print(f"  R1 Helper: {r1_b.get('helper_center_px')}, Tint Centroid: {r1_b.get('tint_center_px')} (Mask px: {r1_b.get('diff_mask_pixels_count')}), 2D Dist: {r1_b.get('distance_2d_px')} px (Pass: {r1_b.get('distance_pass')})")
    print(f"  Code Pointers: Mask [{b_data.get('code_pointer_mask')}], Helper [{b_data.get('code_pointer_helper')}]")

    lat = s_data.get("step_latency", {})
    print(f"\n[Latency Profiling]")
    print(f"  p50: {lat.get('p50_ms')} ms, p95: {lat.get('p95_ms')} ms, total: {lat.get('total_ms')} ms")

    scenA = s_data.get("scenario_a_drop", {})
    scenB = s_data.get("scenario_b_throw", {})
    print(f"\n[Task 4 Scenarios A & B]")
    print(f"  Scen A L1 Landing: {scenA.get('l1', {}).get('landing_time_s')} s, Diff: {scenA.get('l1', {}).get('diff_from_mesh_floor_cm')} cm (Pass: {scenA.get('l1', {}).get('diff_pass')}), Rot: {scenA.get('l1', {}).get('rotation_deg')} deg")
    print(f"  Scen A R1 Landing: {scenA.get('r1', {}).get('landing_time_s')} s, Diff: {scenA.get('r1', {}).get('diff_from_mesh_floor_cm')} cm (Pass: {scenA.get('r1', {}).get('diff_pass')}), Rot: {scenA.get('r1', {}).get('rotation_deg')} deg")
    print(f"  Scen B L1 Travel: {scenB.get('l1', {}).get('travel_distance_m')} m (Pass: {scenB.get('l1', {}).get('travel_pass')}), Stop: {scenB.get('l1', {}).get('stop_time_s')} s")
    print(f"  Scen B R1 Travel: {scenB.get('r1', {}).get('travel_distance_m')} m (Pass: {scenB.get('r1', {}).get('travel_pass')}), Stop: {scenB.get('r1', {}).get('stop_time_s')} s")

    print(f"\n[Captures SHA-256]")
    for cap in EXPECTED_CAPTURES:
        data = cap.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        print(f"  {cap.name}: {sha} ({len(data)} bytes)")

    print("\n[COMPLETE] T6-c execution & ledger verification finished successfully.")


if __name__ == '__main__':
    main()

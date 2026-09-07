#!/usr/bin/env python3
"""
scripts/run_p3_t6b_physics.py

Drives browser to http://localhost:8080/?p3_physics=t6b&t={int(time.time())}
to execute P3-02 T6-b physics suite:
  Task 1: World construction with relocated colliders (manifest centroid / BBox center)
  Task 2: Helper and splat binding with dynamic LineSegments helper
  Task 3: Step latency measurement with performance.now()
  Task 4: Scenario A & B re-evaluation with 6 offline captures
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

WORLD_JSON = RAW_DIR / 't6b_world.json'
WORLD_TXT = RAW_DIR / 't6b_world.txt'
BINDING_JSON = RAW_DIR / 't6b_binding.json'
BINDING_TXT = RAW_DIR / 't6b_binding.txt'
SCENARIOS_JSON = RAW_DIR / 't6b_scenarios.json'
SCENARIOS_TXT = RAW_DIR / 't6b_scenarios.txt'

EXPECTED_CAPTURES = [
    CAPTURES_DIR / "marble_run01_t6b_scenA_t0.png",
    CAPTURES_DIR / "marble_run01_t6b_scenA_landing.png",
    CAPTURES_DIR / "marble_run01_t6b_scenA_final.png",
    CAPTURES_DIR / "marble_run01_t6b_scenB_t0.png",
    CAPTURES_DIR / "marble_run01_t6b_scenB_mid.png",
    CAPTURES_DIR / "marble_run01_t6b_scenB_final.png"
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
    print("  P3-02 T6-b Physics Suite: Collider Relocation & Re-evaluation  ")
    print("==================================================================")

    # Clean previous ledgers/captures if any to ensure fresh creation
    for f in [WORLD_JSON, WORLD_TXT, BINDING_JSON, BINDING_TXT, SCENARIOS_JSON, SCENARIOS_TXT] + EXPECTED_CAPTURES:
        if f.exists():
            f.unlink()

    start_time = time.time()
    url = f"http://localhost:8080/?p3_physics=t6b&t={int(start_time)}"
    navigate_browser(WINDOW_ID, url)

    print("[WAIT] Waiting for T6-b world, binding, and scenarios ledgers and 6 captures...")
    max_wait = 90
    while time.time() - start_time < max_wait:
        all_ledgers = all(f.exists() and f.stat().st_size > 0 for f in [WORLD_JSON, WORLD_TXT, BINDING_JSON, BINDING_TXT, SCENARIOS_JSON, SCENARIOS_TXT])
        all_caps = all(f.exists() and f.stat().st_size > 0 for f in EXPECTED_CAPTURES)
        if all_ledgers and all_caps:
            print(f"[SUCCESS] All ledgers and captures generated in {time.time() - start_time:.1f}s.")
            break
        time.sleep(1.0)
    else:
        raise TimeoutError(f"T6-b physics execution timed out after {max_wait}s.")

    # Validate generated ledgers
    with open(WORLD_JSON, 'r', encoding='utf-8') as f:
        w_data = json.load(f)
    with open(BINDING_JSON, 'r', encoding='utf-8') as f:
        b_data = json.load(f)
    with open(SCENARIOS_JSON, 'r', encoding='utf-8') as f:
        s_data = json.load(f)

    l1_w = w_data.get("dynamic_bodies", {}).get("box_l1", {})
    r1_w = w_data.get("dynamic_bodies", {}).get("box_r1", {})
    print(f"\n[Task 1 World Construction]")
    print(f"  L1 Center Shift: {l1_w.get('center_shift_cm')} cm, 1s Disp: {l1_w.get('displacement_1s_cm')} cm, Pen: {l1_w.get('geometric_penetration_cm')} cm")
    print(f"  R1 Center Shift: {r1_w.get('center_shift_cm')} cm, 1s Disp: {r1_w.get('displacement_1s_cm')} cm, Pen: {r1_w.get('geometric_penetration_cm')} cm")

    l1_b = b_data.get("box_l1", {})
    r1_b = b_data.get("box_r1", {})
    print(f"\n[Task 2 Helper & Splat Binding]")
    print(f"  L1 2D Distance: {l1_b.get('distance_2d_px')} px (Pass: {l1_b.get('distance_pass')})")
    print(f"  R1 2D Distance: {r1_b.get('distance_2d_px')} px (Pass: {r1_b.get('distance_pass')})")

    lat = s_data.get("step_latency", {})
    print(f"\n[Task 3 Step Latency]")
    print(f"  p50: {lat.get('p50_ms')} ms, p95: {lat.get('p95_ms')} ms, total: {lat.get('total_ms')} ms")

    scenA = s_data.get("scenario_a_drop", {})
    scenB = s_data.get("scenario_b_throw", {})
    print(f"\n[Task 4 Scenarios A & B]")
    print(f"  Scen A L1 Landing: {scenA.get('l1', {}).get('landing_time_s')} s, Diff: {scenA.get('l1', {}).get('diff_from_mesh_floor_cm')} cm (Pass: {scenA.get('l1', {}).get('diff_pass')})")
    print(f"  Scen A R1 Landing: {scenA.get('r1', {}).get('landing_time_s')} s, Diff: {scenA.get('r1', {}).get('diff_from_mesh_floor_cm')} cm (Pass: {scenA.get('r1', {}).get('diff_pass')})")
    print(f"  Scen B L1 Travel: {scenB.get('l1', {}).get('travel_distance_m')} m, Stop: {scenB.get('l1', {}).get('stop_time_s')} s")
    print(f"  Scen B R1 Travel: {scenB.get('r1', {}).get('travel_distance_m')} m, Stop: {scenB.get('r1', {}).get('stop_time_s')} s")

    print(f"\n[Captures SHA-256]")
    for cap in EXPECTED_CAPTURES:
        data = cap.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        print(f"  {cap.name}: {sha} ({len(data)} bytes)")

    print("\n[COMPLETE] T6-b execution & ledger verification finished successfully.")


if __name__ == '__main__':
    main()

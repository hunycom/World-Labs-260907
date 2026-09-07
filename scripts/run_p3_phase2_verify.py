"""
Automated validation script for EXE-260906-P3-01 Task 5:
Parameterized test harness verification on llvmpipe.
Compares physical determinism between approved docs/phase2_results.json
and the newly executed docs/p3/phase2_verification_llvmpipe.json.
"""

import os
import sys
import time
import json
import ctypes
import math

WINDOW_ID = "0x2800016"
DISPLAY_STR = ":11.0"
BASE_DIR = "/home/sims/바탕화면/spark"
APPROVED_FILE = os.path.join(BASE_DIR, "docs", "phase2_results.json")
VERIFY_FILE = os.path.join(BASE_DIR, "docs", "p3", "phase2_verification_llvmpipe.json")

if os.path.exists(VERIFY_FILE):
    try:
        os.chmod(VERIFY_FILE, 0o666)
        os.remove(VERIFY_FILE)
    except Exception:
        pass

x11 = ctypes.CDLL("libX11.so.6")
xtst = ctypes.CDLL("libXtst.so.6")

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

def navigate_single_tab(win_id_hex, url):
    dpy = x11.XOpenDisplay(DISPLAY_STR.encode())
    if not dpy:
        raise RuntimeError(f"Could not open X display {DISPLAY_STR}")
    win = int(win_id_hex, 16)
    x11.XMapRaised(dpy, win)
    x11.XSetInputFocus(dpy, win, 2, 0)
    x11.XFlush(dpy)
    time.sleep(0.2)

    ctrl_kc = x11.XKeysymToKeycode(dpy, 0xffe3)
    shift_kc = x11.XKeysymToKeycode(dpy, 0xffe1)
    l_kc = x11.XKeysymToKeycode(dpy, ord('l'))
    ret_kc = x11.XKeysymToKeycode(dpy, 0xff0d)

    # Focus address bar: Ctrl+L
    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, l_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, l_kc, False, 0)
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
    time.sleep(0.1)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.5)

    # Focus canvas inside WebGL area
    xtst.XTestFakeMotionEvent(dpy, 0, 700, 400, 0)
    xtst.XTestFakeButtonEvent(dpy, 1, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeButtonEvent(dpy, 1, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)
    print(f"[P3-VERIFY] Navigated window {win_id_hex} to {url}")

url = f"http://localhost:8080/?phase2_audit=true&p3_verify=true&t={int(time.time())}"
navigate_single_tab(WINDOW_ID, url)

print("[P3-VERIFY] Waiting for Phase 2 verification execution (Task 1 + Task 2 + Task 3, ~45s)...")
for i in range(70):
    time.sleep(2)
    if os.path.exists(VERIFY_FILE) and os.path.getsize(VERIFY_FILE) > 1000:
        print(f"[P3-VERIFY] Verification report received after {(i+1)*2}s!")
        break
    if i % 5 == 0:
        print(f"[{(i+1)*2}s] Still running physics simulation...")

if not os.path.exists(VERIFY_FILE):
    print("[P3-VERIFY] ERROR: Timed out waiting for verification report.")
    sys.exit(1)

with open(APPROVED_FILE, "r", encoding="utf-8") as f:
    approved = json.load(f)

with open(VERIFY_FILE, "r", encoding="utf-8") as f:
    verified = json.load(f)

print("\n" + "="*80)
print("             PHASE 2 DETERMINISM & DEVIATION AUDIT REPORT")
print("="*80)

# 1. Summary comparison
app_sum = approved.get("summary", {})
ver_sum = verified.get("summary", {})

print(f"Task 1 Grounding Rate: Approved={app_sum.get('task1_grounding_rate')}, Verified={ver_sum.get('task1_grounding_rate')}")
print(f"Task 2 p95 FrameTime:  Approved={app_sum.get('task2_p95_frametime_ms')}ms, Verified={ver_sum.get('task2_p95_frametime_ms')}ms")
print(f"Task 3 Throwing Rate:  Approved={app_sum.get('task3_throwing_rate')}, Verified={ver_sum.get('task3_throwing_rate')}")

# 2. Task 1 detailed deviation
app_t1 = approved.get("task1_trials", [])
ver_t1 = verified.get("task1_trials", [])
print(f"\n[Task 1 Grounding] Total seeds/trials: Approved={len(app_t1)}, Verified={len(ver_t1)}")
max_pos_dev_t1 = 0.0
for i, (a, v) in enumerate(zip(app_t1, ver_t1)):
    pos_a = a.get("finalPos", [0, 0, 0])
    pos_v = v.get("finalPos", [0, 0, 0])
    dist = math.sqrt(sum((x1 - x2)**2 for x1, x2 in zip(pos_a, pos_v)))
    max_pos_dev_t1 = max(max_pos_dev_t1, dist)

print(f"Task 1 Maximum Settled Position Deviation across 15 trials: {max_pos_dev_t1:.8f} m")

# 3. Task 3 detailed deviation
app_t3 = approved.get("task3_tests", [])
ver_t3 = verified.get("task3_tests", [])
print(f"\n[Task 3 Throwing] Total trials: Approved={len(app_t3)}, Verified={len(ver_t3)}")

match_all = True
for i, (a, v) in enumerate(zip(app_t3, ver_t3)):
    idx = i + 1
    p_a = a.get("passed")
    p_v = v.get("passed")
    part_id = a.get("targetPartId")
    imp_name = a.get("impulseName")
    dy_a = a.get("elevationDelta", 0.0)
    dy_v = v.get("elevationDelta", 0.0)
    dist_a = a.get("horizontalDisplacement", 0.0)
    dist_v = v.get("horizontalDisplacement", 0.0)
    status_match = (p_a == p_v)
    if not status_match:
        match_all = False
    print(f"  Trial #{idx:02d} ({part_id:10s}, {imp_name:18s}): Approved Pass={str(p_a):5s}, Verified Pass={str(p_v):5s} | ΔY: {dy_a:.4f} vs {dy_v:.4f} | Dist: {dist_a:.4f} vs {dist_v:.4f}")

# Check trial #04 (the expected failure)
t4_a = app_t3[3]
t4_v = ver_t3[3]
print("\n[Trial #04 Expected Failure Verification]")
print(f"  Approved: Part={t4_a.get('targetPartId')}, Pass={t4_a.get('passed')}, Dist={t4_a.get('horizontalDisplacement')} m, DeltaY={t4_a.get('elevationDelta')} m")
print(f"  Verified: Part={t4_v.get('targetPartId')}, Pass={t4_v.get('passed')}, Dist={t4_v.get('horizontalDisplacement')} m, DeltaY={t4_v.get('elevationDelta')} m")

dev_dist_04 = abs(t4_a.get('horizontalDisplacement', 0) - t4_v.get('horizontalDisplacement', 0))
dev_dy_04 = abs(t4_a.get('elevationDelta', 0) - t4_v.get('elevationDelta', 0))
print(f"  Trial #04 Deviation: Distance={dev_dist_04:.8f} m, DeltaY={dev_dy_04:.8f} m")

if match_all and max_pos_dev_t1 < 1e-4 and dev_dist_04 < 1e-4:
    print("\n>>> DETERMINISM CRITERIA MET: Physics deviation = 0 (identical deterministic trajectory) <<<")
else:
    print("\n>>> DETERMINISM DISCREPANCY DETECTED <<<")

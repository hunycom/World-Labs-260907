import os
import sys
import time
import subprocess
import json
import ctypes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE_SCRIPT = os.path.join(BASE_DIR, "scripts/capture_window.py")
REPORT_PATH = os.path.join(BASE_DIR, "docs/audit_results_browser.json")
WINDOW_ID = "0x2800016"
DISPLAY_STR = ":11.0"

if os.path.exists(REPORT_PATH):
    os.remove(REPORT_PATH)

x11 = ctypes.CDLL("libX11.so.6")
xtst = ctypes.CDLL("libXtst.so.6")

def send_key_event(dpy, keycode, is_press):
    xtst.XTestFakeKeyEvent(dpy, keycode, is_press, 0)
    x11.XFlush(dpy)

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
    else:
        kc = x11.XKeysymToKeycode(dpy, ord(ch))
        xtst.XTestFakeKeyEvent(dpy, kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.008)

def navigate_single_tab_foreground(win_id_hex, url):
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
    time.sleep(0.04)
    xtst.XTestFakeKeyEvent(dpy, l_kc, True, 0)
    time.sleep(0.04)
    xtst.XTestFakeKeyEvent(dpy, l_kc, False, 0)
    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.2)

    # Type URL
    for ch in url:
        send_char(dpy, ch, shift_kc)

    # Press Enter
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.5)

    # Focus canvas inside WebGL area to ensure active rendering
    xtst.XTestFakeMotionEvent(dpy, 0, 700, 400, 0)
    xtst.XTestFakeButtonEvent(dpy, 1, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeButtonEvent(dpy, 1, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)
    print(f"[ORCHESTRATOR] Successfully navigated single-tab Firefox window {win_id_hex} to {url}")

print(f"[ORCHESTRATOR] Commencing Single-Tab Foreground Audit Run on Window {WINDOW_ID}...")
audit_url = f"http://localhost:8080/?audit=true&t={int(time.time())}"
navigate_single_tab_foreground(WINDOW_ID, audit_url)

print("[ORCHESTRATOR] Monitoring audit progress in foreground single-tab...")
t_start = time.time()
head_captured = False
wing_captured = False

while time.time() - t_start < 60:
    elapsed = time.time() - t_start
    if elapsed >= 18.0 and not head_captured:
        print(f"[ORCHESTRATOR] Capturing Head Picked Screenshot at {elapsed:.1f}s...")
        subprocess.run([sys.executable, CAPTURE_SCRIPT, WINDOW_ID, os.path.join(BASE_DIR, "docs/screenshot_head_picked.png"), DISPLAY_STR])
        head_captured = True
    elif elapsed >= 21.0 and not wing_captured:
        print(f"[ORCHESTRATOR] Capturing Wing Picked Screenshot at {elapsed:.1f}s...")
        subprocess.run([sys.executable, CAPTURE_SCRIPT, WINDOW_ID, os.path.join(BASE_DIR, "docs/screenshot_wing_picked.png"), DISPLAY_STR])
        wing_captured = True

    if os.path.exists(REPORT_PATH) and head_captured and wing_captured:
        print(f"[ORCHESTRATOR] Report generated at {REPORT_PATH} in {elapsed:.1f}s!")
        break
    time.sleep(0.5)

if os.path.exists(REPORT_PATH):
    data = None
    for _ in range(10):
        try:
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data and "summary" in data:
                break
        except Exception:
            time.sleep(0.5)
    if data:
        print("\n=== AUDIT REPORT SUMMARY ===")
        print(json.dumps(data.get("summary", {}), indent=2))
    else:
        print("[ORCHESTRATOR] Warning: Could not parse report.")
else:
    print("[ORCHESTRATOR] Warning: Timed out waiting for report.")

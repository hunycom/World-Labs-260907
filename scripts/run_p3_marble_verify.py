#!/usr/bin/env python3
"""
scripts/run_p3_marble_verify.py

Automation driver for EXE-260906-P3-02-FIX:
Triggers Spark runtime SplatMesh loading of run01_500k.spz,
semantics transformation, 10s frame telemetry collection,
and offline captures via captureFrame in Firefox on DISPLAY :11.0.
"""

import os
import sys
import time
import ctypes
import json
from pathlib import Path

WINDOW_ID = "0x2800016"
DISPLAY_STR = ":11.0"
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures"
METRICS_JSON = RAW_DIR / "spark_load_metrics_run01.json"

if METRICS_JSON.exists():
    METRICS_JSON.unlink()

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


def navigate_browser(win_id_hex: str, url: str):
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

    # Type URL
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

    # Click on WebGL canvas to focus
    xtst.XTestFakeMotionEvent(dpy, 0, 700, 400, 0)
    xtst.XTestFakeButtonEvent(dpy, 1, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeButtonEvent(dpy, 1, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)
    print(f"[P3-MARBLE] Navigated Firefox ({win_id_hex}) to {url}")


def main():
    print("==================================================================")
    print("  EXE-260906-P3-02-FIX: Spark Runtime Loading & Capture Execution")
    print("==================================================================")
    
    url = f"http://localhost:8080/?p3_marble=run01&t={int(time.time())}"
    navigate_browser(WINDOW_ID, url)

    print("[*] Waiting for telemetry report (loading + 10s benchmark + 4 captures)...")
    success = False
    for i in range(45):  # Wait up to 90 seconds
        time.sleep(2)
        if METRICS_JSON.exists() and METRICS_JSON.stat().st_size > 100:
            try:
                with open(METRICS_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                print("\n[+] Telemetry report successfully received from browser runtime!")
                print(f"    - Renderer:     {data.get('renderer')}")
                print(f"    - Splat Count:  {data.get('num_splats'):,} splats")
                print(f"    - Load Time:    {data.get('load_time_ms')} ms")
                print(f"    - Frame p50:    {data.get('frame_time_p50_ms')} ms")
                print(f"    - Frame p95:    {data.get('frame_time_p95_ms')} ms")
                print(f"    - Average FPS:  {data.get('average_fps')} fps")
                print(f"    - Captures:")
                for k, v in data.get("captures", {}).items():
                    print(f"        * {k:15s}: {v.get('label')}.png (sha256: {v.get('sha256')})")
                success = True
                break
            except Exception as e:
                pass
        print(f"    [{(i+1)*2}s] Waiting for browser runtime...", end="\r", flush=True)

    if not success:
        print("\n[ERROR] Timed out waiting for spark_load_metrics_run01.json.", file=sys.stderr)
        sys.exit(1)

    print("\n==================================================================")
    print("  Spark Runtime Telemetry Verification: PASS")
    print("==================================================================")


if __name__ == "__main__":
    main()

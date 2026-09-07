#!/usr/bin/env python3
"""
scripts/run_p3_t6_physics.py

Drives browser to http://localhost:8080/?p3_physics=t6&t={int(time.time())}
to execute P3-02 T6 physics world construction, drop & throw scenarios, and determinism verification.
Waits for all 3 ledger files and 6 offline captures to be written.
"""

import time
import ctypes
import json
from pathlib import Path

WINDOW_ID = '0x2800016'
DISPLAY_STR = ':11.0'
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / 'docs' / 'p3' / 'raw'
CAPTURES_DIR = ROOT_DIR / 'docs' / 'p3' / 'captures'

WORLD_JSON = RAW_DIR / 't6_world.json'
WORLD_TXT = RAW_DIR / 't6_world.txt'
SCENARIOS_JSON = RAW_DIR / 't6_scenarios.json'
SCENARIOS_TXT = RAW_DIR / 't6_scenarios.txt'
DETERMINISM_JSON = RAW_DIR / 't6_determinism.json'
DETERMINISM_TXT = RAW_DIR / 't6_determinism.txt'

EXPECTED_CAPTURES = [
    CAPTURES_DIR / "marble_run01_t6_scenA_t0.png",
    CAPTURES_DIR / "marble_run01_t6_scenA_landing.png",
    CAPTURES_DIR / "marble_run01_t6_scenA_final.png",
    CAPTURES_DIR / "marble_run01_t6_scenB_t0.png",
    CAPTURES_DIR / "marble_run01_t6_scenB_mid.png",
    CAPTURES_DIR / "marble_run01_t6_scenB_final.png"
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
    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.4)

    for ch in url:
        send_char(dpy, ch, shift_kc)

    time.sleep(0.15)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)


def main():
    target_url = f"http://localhost:8080/?p3_physics=t6&t={int(time.time())}"
    print(f"[*] Navigating browser {WINDOW_ID} to {target_url}...")

    # Clear previous ledgers to ensure fresh execution
    for f in [WORLD_JSON, WORLD_TXT, SCENARIOS_JSON, SCENARIOS_TXT, DETERMINISM_JSON, DETERMINISM_TXT] + EXPECTED_CAPTURES:
        if f.exists():
            f.unlink()

    t_start = time.time()
    navigate_browser(WINDOW_ID, target_url)

    print("[*] Waiting for P3-02 T6 physics suite completion from browser...")
    timeout = 180
    for i in range(timeout):
        time.sleep(1.0)
        all_ledgers = all(p.exists() for p in [WORLD_JSON, WORLD_TXT, SCENARIOS_JSON, SCENARIOS_TXT, DETERMINISM_JSON, DETERMINISM_TXT])
        all_caps = all(p.exists() for p in EXPECTED_CAPTURES)
        if all_ledgers and all_caps:
            print(f"[+] P3-02 T6 Physics Suite completed in {time.time() - t_start:.2f}s!")
            print("\n--- World Ledger ---")
            print(WORLD_TXT.read_text(encoding="utf-8"))
            print("\n--- Scenarios Ledger ---")
            print(SCENARIOS_TXT.read_text(encoding="utf-8"))
            print("\n--- Determinism Ledger ---")
            print(DETERMINISM_TXT.read_text(encoding="utf-8"))
            return

        if i > 0 and i % 10 == 0:
            ledgers_done = sum(1 for p in [WORLD_JSON, SCENARIOS_JSON, DETERMINISM_JSON] if p.exists())
            caps_done = sum(1 for p in EXPECTED_CAPTURES if p.exists())
            print(f"[*] Elapsed: {i}s (Ledgers: {ledgers_done}/3, Captures: {caps_done}/6)...")

    raise TimeoutError(f"P3-02 T6 physics suite did not complete within {timeout} seconds.")


if __name__ == "__main__":
    main()

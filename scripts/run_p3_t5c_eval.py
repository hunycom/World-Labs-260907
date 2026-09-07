#!/usr/bin/env python3
"""
scripts/run_p3_t5c_eval.py

Drives browser to http://localhost:8080/?p3_pick_eval=t5c
to execute single-run picking evaluation (Policy v1 & Policy v2 simultaneously)
on the new frozen holdout dataset tests/p3/t5c_holdout_clicks.json (seed=20260908, 225 clicks).
Strictly 1-run execution.
"""

import time
import ctypes
import json
from pathlib import Path

WINDOW_ID = '0x2800016'
DISPLAY_STR = ':11.0'
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / 'docs' / 'p3' / 'raw'
EVAL_JSON = RAW_DIR / 't5c_pick_eval.json'
EVAL_TXT = RAW_DIR / 't5c_pick_eval.txt'

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
    time.sleep(0.2)

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
    time.sleep(0.3)

    for ch in url:
        send_char(dpy, ch, shift_kc)

    time.sleep(0.1)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)


def main():
    target_url = f"http://localhost:8080/?p3_pick_eval=t5c&t={int(time.time())}"
    print(f"[*] Navigating browser {WINDOW_ID} to {target_url}...")
    if EVAL_JSON.exists():
        EVAL_JSON.unlink()
    if EVAL_TXT.exists():
        EVAL_TXT.unlink()

    t_start = time.time()
    navigate_browser(WINDOW_ID, target_url)

    print("[*] Waiting for P3-02 T5-c single-run holdout evaluation completion from browser...")
    for _ in range(120):
        time.sleep(1.0)
        if EVAL_JSON.exists() and EVAL_TXT.exists():
            print(f"[+] Single-run holdout evaluation completed in {time.time() - t_start:.2f}s!")
            data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
            print(EVAL_TXT.read_text(encoding="utf-8"))
            return

    raise TimeoutError("Holdout evaluation did not complete within 120 seconds.")


if __name__ == "__main__":
    main()

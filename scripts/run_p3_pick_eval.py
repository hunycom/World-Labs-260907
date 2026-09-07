#!/usr/bin/env python3
"""
scripts/run_p3_pick_eval.py

EXE-260906-P3-02-T5 Task 2: Single-Run Holdout Picking Evaluation Driver
Drives browser to http://localhost:8080/?p3_pick_eval=t5
Waits for single-run evaluation completion and verifies docs/p3/raw/t5_pick_eval.json.
Strictly 1-run evaluation policy: no re-runs!
"""

import time
import ctypes
import json
from pathlib import Path

WINDOW_ID = '0x2800016'
DISPLAY_STR = ':11.0'
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / 'docs' / 'p3' / 'raw'
EVAL_JSON = RAW_DIR / 't5_pick_eval.json'
EVAL_TXT = RAW_DIR / 't5_pick_eval.txt'

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
    print("==================================================================")
    print("  EXE-260906-P3-02-T5 Task 2: Single-Run Picking Evaluation Driver")
    print("==================================================================")

    if EVAL_JSON.exists():
        EVAL_JSON.unlink()
    if EVAL_TXT.exists():
        EVAL_TXT.unlink()

    url = f'http://localhost:8080/?p3_pick_eval=t5&t={int(time.time())}'
    print(f"[*] Navigating Firefox ({WINDOW_ID}) to {url}")
    navigate_browser(WINDOW_ID, url)

    print("[*] Waiting for single-run evaluation completion...")
    for i in range(60):
        time.sleep(2)
        if EVAL_JSON.exists() and EVAL_JSON.stat().st_size > 50:
            print("\n[+] Browser finished single-run picking evaluation!")
            break
        print(f"    [{(i+1)*2}s] Evaluating...", end="\r", flush=True)

    time.sleep(1)

    if not EVAL_JSON.exists():
        print(f"\n[ERROR] Evaluation timed out. File not found: {EVAL_JSON}")
        return

    data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    print("\n" + "=" * 66)
    print("  EXE-260906-P3-02-T5 Task 2 Evaluation Summary")
    print("=" * 66)
    print(f"Total Samples Evaluated: {data.get('total_eval_samples')}")
    print(f"Dynamic Accuracy:        {data.get('dynamic_success_count')}/{data.get('dynamic_samples_count')} ({data.get('dynamic_accuracy_pct')}%) | Pass: {data.get('dynamic_pass')}")
    print(f"Static False Positives:  {data.get('static_false_positive_count')}/{data.get('static_samples_count')} ({data.get('static_fpr_pct')}%) | Pass: {data.get('static_pass')}")
    print(f"Latency:                 p50={data.get('latency_p50_ms')}ms, p95={data.get('latency_p95_ms')}ms ({data.get('renderer_info')})")
    print("=" * 66)


if __name__ == '__main__':
    main()

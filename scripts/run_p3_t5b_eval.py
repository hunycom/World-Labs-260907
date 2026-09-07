#!/usr/bin/env python3
"""
scripts/run_p3_t5b_eval.py

Drives browser to http://localhost:8080/?p3_pick_eval=t5b
to execute the single-run holdout picking evaluation (225 clicks).
Strict 1-Run Policy: This script executes strictly once.
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
EVAL_JSON = RAW_DIR / 't5b_pick_eval.json'
EVAL_TXT = RAW_DIR / 't5b_pick_eval.txt'
HOLDOUT_JSON = ROOT_DIR / 'tests' / 'p3' / 't5_holdout_clicks.json'
EXPECTED_SHA = '9d86f61fe0254a7de8e3b4263a2feea2749a87e9adb28a866a230ba4d6a49458'

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


def run_eval():
    print("==================================================================")
    print("  EXE-260906-P3-02-T5-b Task 3: Single-Run Holdout Picking Evaluation")
    print("==================================================================")

    # 1. Verify frozen holdout SHA
    holdout_bytes = HOLDOUT_JSON.read_bytes()
    actual_sha = hashlib.sha256(holdout_bytes).hexdigest()
    print(f"[*] Holdout SHA-256: {actual_sha}")
    if actual_sha != EXPECTED_SHA:
        raise ValueError(f"Holdout SHA mismatch! Expected {EXPECTED_SHA}, got {actual_sha}")
    print("    -> Frozen holdout bit-identical verification: PASS")

    if EVAL_JSON.exists():
        EVAL_JSON.unlink()
    if EVAL_TXT.exists():
        EVAL_TXT.unlink()

    url = f'http://localhost:8080/?p3_pick_eval=t5b&t={int(time.time())}'
    print(f"[*] Navigating Firefox ({WINDOW_ID}) to single-run evaluation: {url}")
    navigate_browser(WINDOW_ID, url)

    print("[*] Waiting for 225 holdout picking evaluations across V1, V2, V3...")
    for i in range(60):
        time.sleep(2)
        if EVAL_JSON.exists() and EVAL_JSON.stat().st_size > 500:
            print(f"\n[+] Single-run evaluation results received!")
            break
        print(f"    [{(i+1)*2}s] Evaluating...", end="\r", flush=True)

    if not EVAL_JSON.exists():
        raise TimeoutError("Evaluation timed out.")

    data = json.loads(EVAL_JSON.read_text(encoding="utf-8"))
    return data


if __name__ == '__main__':
    data = run_eval()
    print("\n------------------------------------------------------------------")
    print(f"Total Samples:          {data.get('total_eval_samples')} clicks")
    print(f"Dynamic Accuracy:       {data.get('dynamic_success_count')} / {data.get('dynamic_samples_count')} ({data.get('dynamic_accuracy_pct')}%) [Pass: {data.get('dynamic_pass')}]")
    print(f"Static False Positives: {data.get('static_false_positive_count')} / {data.get('static_samples_count')} ({data.get('static_fpr_pct')}%) [Pass: {data.get('static_pass')}]")
    print(f"Zero-Hit Coordinates:   {data.get('zero_hit_coordinates_count')} clicks")
    print(f"Latency:                p50 = {data.get('latency_p50_ms')} ms, p95 = {data.get('latency_p95_ms')} ms")
    print("------------------------------------------------------------------")
    print("Per-View Breakdown:")
    for vk in ["V1", "V2", "V3"]:
        vs = data.get('per_view_stats', {}).get(vk, {})
        print(f"  {vk}: Dynamic Acc = {vs.get('dynamic_accuracy_pct')}% ({vs.get('dynamic_success_count')}/{vs.get('dynamic_samples_count')}), Static FPR = {vs.get('static_fpr_pct')}%")
    print("------------------------------------------------------------------")
    print("Per-Part Breakdown:")
    for pk in ["box_l1", "box_r1"]:
        ps = data.get('per_part_stats', {}).get(pk, {})
        print(f"  {pk}: Accuracy = {ps.get('dynamic_accuracy_pct')}% ({ps.get('dynamic_success_count')}/{ps.get('dynamic_samples_count')})")
    print("==================================================================")

#!/usr/bin/env python3
"""
scripts/run_p3_partition_capture.py

Drives browser to http://localhost:8080/?p3_partition=run01
Captures 3 SplatEdit partition views (front, iso, selected)
and persists results to docs/p3/captures/
"""

import time
import ctypes
import json
import hashlib
from pathlib import Path

WINDOW_ID = '0x2800016'
DISPLAY_STR = ':11.0'
ROOT_DIR = Path(__file__).resolve().parent.parent
CAPTURES_DIR = ROOT_DIR / 'docs' / 'p3' / 'captures'
TELEMETRY_JSON = CAPTURES_DIR / 'marble_run01_part_telemetry.meta.json'

if TELEMETRY_JSON.exists():
    TELEMETRY_JSON.unlink()

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
    time.sleep(0.1)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.5)

    xtst.XTestFakeMotionEvent(dpy, 0, 700, 400, 0)
    xtst.XTestFakeButtonEvent(dpy, 1, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeButtonEvent(dpy, 1, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)
    print(f'[P3-PART] Navigated Firefox ({win_id_hex}) to {url}')


def find_firefox_window(dpy):
    root = x11.XDefaultRootWindow(dpy)
    root_r = ctypes.c_ulong()
    parent_r = ctypes.c_ulong()
    children_r = ctypes.POINTER(ctypes.c_ulong)()
    nchildren_r = ctypes.c_uint()
    x11.XQueryTree(dpy, root, ctypes.byref(root_r), ctypes.byref(parent_r), ctypes.byref(children_r), ctypes.byref(nchildren_r))
    for i in range(nchildren_r.value):
        w = children_r[i]
        name_ptr = ctypes.c_char_p()
        if x11.XFetchName(dpy, w, ctypes.byref(name_ptr)) and name_ptr.value:
            title = name_ptr.value.decode("utf-8", errors="ignore")
            if "Firefox" in title:
                return hex(w)
    return "0x2800001"


def main():
    print('==================================================================')
    print('  EXE-260906-P3-02-T4B-R4 Task 4: 14 Offline Captures Suite')
    print('==================================================================')
    
    url = f'http://localhost:8080/?p3_partition=run01&t={int(time.time())}'
    win_id = '0x2800016'
    
    print(f'[*] Target Firefox window ID: {win_id}')
    try:
        navigate_browser(win_id, url)
    except Exception as e:
        print(f'[WARN] X11 navigation failed: {e}. Launching via subprocess...')
        import subprocess, os
        env = os.environ.copy()
        env['DISPLAY'] = DISPLAY_STR
        subprocess.Popen(['firefox', url], env=env)

    print('[*] Waiting for 14 Multi-SplatMesh partition captures (front, iso, 6 ON closeups, 6 OFF closeups)...')
    for i in range(50):
        time.sleep(2)
        if TELEMETRY_JSON.exists() and TELEMETRY_JSON.stat().st_size > 50:
            print("\n[+] Browser finished Discrete Multi-SplatMesh partition captures!")
            break
        print(f"    [{(i+1)*2}s] Capturing...", end="\r", flush=True)

    time.sleep(1)
    
    # Verify T5 capture files
    captures = [
        ("marble_run01_part_front.png", "정면 2개 동적 상자 틴트 캡처 (ON)"),
        ("marble_run01_part_iso.png", "조감 45도 동적 상자 배치 캡처 (ON)"),
        ("marble_run01_part_selected_l1.png", "L1 상자 전방 2.3m 근접 조준 캡처 (ON)"),
        ("marble_run01_part_selected_l1_off.png", "L1 상자 전방 2.3m 동일 시점 캡처 (OFF)"),
        ("marble_run01_part_selected_r1.png", "R1 상자 전방 2.3m 근접 조준 캡처 (ON)"),
        ("marble_run01_part_selected_r1_off.png", "R1 상자 전방 2.3m 동일 시점 캡처 (OFF)"),
        ("marble_run01_view_v1_on.png", "V1 정면 뷰 틴트 캡처 (ON)"),
        ("marble_run01_view_v1_off.png", "V1 정면 뷰 원색 캡처 (OFF)"),
        ("marble_run01_view_v2_on.png", "V2 L1 집중 뷰 틴트 캡처 (ON)"),
        ("marble_run01_view_v2_off.png", "V2 L1 집중 뷰 원색 캡처 (OFF)"),
        ("marble_run01_view_v3_on.png", "V3 R1 집중 뷰 틴트 캡처 (ON)"),
        ("marble_run01_view_v3_off.png", "V3 R1 집중 뷰 원색 캡처 (OFF)"),
    ]
    
    print("\n[*] T5 Partition & View Captures Verification:")
    for fn, desc in captures:
        fp = CAPTURES_DIR / fn
        if fp.exists():
            sz = fp.stat().st_size
            h = hashlib.sha256(fp.read_bytes()).hexdigest()
            print(f'  [+] {fn} ({desc}): {sz:,} B | SHA256={h[:16]}...{h[-8:]}')
        else:
            print(f'  [WARN] Missing capture file: {fp}')


if __name__ == '__main__':
    main()

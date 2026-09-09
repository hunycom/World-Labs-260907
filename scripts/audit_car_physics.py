#!/usr/bin/env python3
"""
scripts/audit_car_physics.py

Orchestrates the verification audit suite for Car Physics 3D (EXE-260909-CAR-02):
- Launches local HTTP server with WASM/SPZ/JS support on port 8089.
- Navigates Firefox to http://127.0.0.1:8089/car-physics.html?audit=true.
- Receives WebGL canvas captures and physical telemetry via POST /api/save_audit.
- Also captures full OS window screenshot for HUD audit.
- Verifies all 5 audit stages: t0 rest, 5s rest drift, [R] drop in air, [R] landed, lateral push.
- Outputs docs/car/physics_audit_result.json and 12 screenshot assets.
"""

import http.server
import socketserver
import threading
import time
import os
import sys
import json
import base64
import ctypes
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_CAR = ROOT_DIR / "docs" / "car"
DOCS_CAR.mkdir(parents=True, exist_ok=True)

AUDIT_PORT = 8095
DISPLAY_STR = ":11.0"
WINDOW_ID = "0x1000016"

try:
    x11 = ctypes.CDLL("libX11.so.6")
    xtst = ctypes.CDLL("libXtst.so.6")
except Exception as e:
    print(f"[WARN] Failed to load libX11/libXtst: {e}")
    x11 = None
    xtst = None

audit_completed_event = threading.Event()

class AuditHTTPHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".spz": "application/octet-stream",
        ".glb": "model/gltf-binary",
        ".wasm": "application/wasm",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".json": "application/json",
    }

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/save_audit":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body)

            label = payload.get("label", "unknown")
            data_url = payload.get("dataUrl")
            meta = payload.get("meta")

            if data_url and "," in data_url:
                header, b64_data = data_url.split(",", 1)
                img_bytes = base64.b64decode(b64_data)
                out_png = DOCS_CAR / f"{label}.png"
                out_png.write_bytes(img_bytes)
                print(f"[+] Saved screenshot: {out_png.name} ({len(img_bytes):,} bytes)")

            if meta is not None:
                out_json = DOCS_CAR / f"{label}.json"
                out_json.write_text(json.dumps(meta, indent=2), encoding="utf-8")
                print(f"[+] Saved audit metadata: {out_json.name}")

            if label == "physics_audit_result":
                audit_completed_event.set()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{\"status\":\"ok\"}")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        if "GET" in format % args and any(ext in format % args for ext in [".spz", ".js", ".png", ".css", ".glb"]):
            return
        print(f"[HTTP] {format % args}")


def send_char(dpy, ch, shift_kc):
    if ch == ":":
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        semi_kc = x11.XKeysymToKeycode(dpy, ord(";"))
        xtst.XTestFakeKeyEvent(dpy, semi_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, semi_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == "?":
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        slash_kc = x11.XKeysymToKeycode(dpy, ord("/"))
        xtst.XTestFakeKeyEvent(dpy, slash_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, slash_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == "&":
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        seven_kc = x11.XKeysymToKeycode(dpy, ord("7"))
        xtst.XTestFakeKeyEvent(dpy, seven_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, seven_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == "_":
        xtst.XTestFakeKeyEvent(dpy, shift_kc, True, 0)
        time.sleep(0.01)
        minus_kc = x11.XKeysymToKeycode(dpy, ord("-"))
        xtst.XTestFakeKeyEvent(dpy, minus_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, minus_kc, False, 0)
        xtst.XTestFakeKeyEvent(dpy, shift_kc, False, 0)
    elif ch == "=":
        equal_kc = x11.XKeysymToKeycode(dpy, ord("="))
        xtst.XTestFakeKeyEvent(dpy, equal_kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, equal_kc, False, 0)
    else:
        kc = x11.XKeysymToKeycode(dpy, ord(ch))
        xtst.XTestFakeKeyEvent(dpy, kc, True, 0)
        xtst.XTestFakeKeyEvent(dpy, kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.008)


def navigate_firefox(win_id_hex: str, url: str):
    if not x11 or not xtst:
        print("[WARN] X11 libraries not available for keystroke navigation.")
        return False
    dpy = x11.XOpenDisplay(DISPLAY_STR.encode())
    if not dpy:
        print(f"[WARN] Could not open X display {DISPLAY_STR}")
        return False
    win = int(win_id_hex, 16)
    x11.XMapRaised(dpy, win)
    x11.XSetInputFocus(dpy, win, 2, 0)
    x11.XFlush(dpy)
    time.sleep(0.3)

    ctrl_kc = x11.XKeysymToKeycode(dpy, 0xffe3)
    shift_kc = x11.XKeysymToKeycode(dpy, 0xffe1)
    l_kc = x11.XKeysymToKeycode(dpy, ord("l"))
    ret_kc = x11.XKeysymToKeycode(dpy, 0xff0d)

    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, l_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, l_kc, False, 0)
    xtst.XTestFakeKeyEvent(dpy, ctrl_kc, False, 0)
    x11.XFlush(dpy)
    time.sleep(0.2)

    for ch in url:
        send_char(dpy, ch, shift_kc)

    time.sleep(0.1)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, True, 0)
    time.sleep(0.05)
    xtst.XTestFakeKeyEvent(dpy, ret_kc, False, 0)
    x11.XFlush(dpy)
    x11.XCloseDisplay(dpy)
    print(f"[+] Sent navigation command to window {win_id_hex} -> {url}")
    return True


def capture_window_xwd(win_id=WINDOW_ID, out_path="docs/car/test_full_window.png"):
    cmd = ["xwd", "-id", win_id, "-silent", "-display", DISPLAY_STR, "-out", "/tmp/win_audit.xwd"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return False
    # Run conversion with current python executable
    script = f"""
import struct, numpy as np, cv2
with open("/tmp/win_audit.xwd", "rb") as f:
    hdr_sz = struct.unpack(">I", f.read(4))[0]
    f.seek(0)
    header = f.read(hdr_sz)
    fields = struct.unpack(">22I", header[:88])
    w, h = fields[4], fields[5]
    bpp, bpl = fields[11], fields[12]
    ncolors = fields[19]
    f.seek(hdr_sz + ncolors * 12)
    raw = f.read()
arr = np.frombuffer(raw[:h * bpl], dtype=np.uint8).reshape((h, bpl))
img = arr[:, :w * 4].reshape((h, w, 4))[:, :, :3]
cv2.imwrite("{out_path}", img)
"""
    subprocess.run([sys.executable, "-c", script], capture_output=True)
    return Path(out_path).exists()


def main():
    print("==================================================================")
    print("  EXE-260909-CAR-02: Car Physics 3D Automated Audit Orchestrator")
    print("==================================================================")

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    os.chdir(str(ROOT_DIR))
    server = ReusableTCPServer(("0.0.0.0", AUDIT_PORT), AuditHTTPHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print(f"[+] HTTP Server running at http://127.0.0.1:{AUDIT_PORT}")

    target_url = f"http://127.0.0.1:{AUDIT_PORT}/car-physics.html?audit=true&t={int(time.time())}"

    nav_ok = navigate_firefox(WINDOW_ID, target_url)
    if not nav_ok:
        print("[*] Launching Firefox via subprocess...")
        env = os.environ.copy()
        env["DISPLAY"] = DISPLAY_STR
        subprocess.Popen(["firefox", target_url], env=env)

    print("[*] Waiting for browser test suite to execute and submit results...")
    max_wait_s = 40
    start_time = time.time()
    while time.time() - start_time < max_wait_s:
        if audit_completed_event.is_set():
            print("\n[+] Audit completion event received from browser!")
            break
        elapsed = int(time.time() - start_time)
        print(f"    [{elapsed}s / {max_wait_s}s] Running test steps in browser...", end="\r", flush=True)
        time.sleep(1.0)

    full_win_path = DOCS_CAR / "test_full_window.png"
    capture_window_xwd(WINDOW_ID, str(full_win_path))
    if full_win_path.exists():
        print(f"[+] Captured full window UI: {full_win_path} ({full_win_path.stat().st_size:,} bytes)")

    # Generate Side-by-Side Comparison Composite
    try:
        from scripts.create_side_by_side import create_comparison
        create_comparison()
    except Exception as e:
        print(f"[WARN] Failed to generate side-by-side comparison: {e}")

    result_json = DOCS_CAR / "physics_audit_result.json"
    if result_json.exists():
        data = json.loads(result_json.read_text(encoding="utf-8"))
        print("\n==================================================================")
        print("  AUTOMATED AUDIT RESULT SUMMARY:")
        print("==================================================================")
        print(json.dumps(data, indent=2))
    else:
        print(f"\n[WARN] physics_audit_result.json not found yet.")

    server.shutdown()
    print("[+] Audit Orchestration Finished.")

if __name__ == "__main__":
    main()

import os
import sys
import struct
import subprocess
import numpy as np
import cv2

def capture_window(win_id="0x2800016", out_path="docs/screenshot.png", display=":11.0"):
    tmp_xwd = f"/tmp/win_{win_id}.xwd"
    cmd = ["xwd", "-id", win_id, "-silent", "-display", display, "-out", tmp_xwd]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error capturing window: {res.stderr}")
        return False

    with open(tmp_xwd, "rb") as f:
        header_size = struct.unpack(">I", f.read(4))[0]
        f.seek(0)
        header = f.read(header_size)
        fields = struct.unpack(">22I", header[:88])
        width, height = fields[4], fields[5]
        bpp, bpl = fields[11], fields[12]
        ncolors = fields[19]
        f.seek(header_size + ncolors * 12)
        raw = f.read()

    arr = np.frombuffer(raw[:height * bpl], dtype=np.uint8).reshape((height, bpl))
    img = arr[:, :width * 4].reshape((height, width, 4))
    bgr = img[:, :, :3]
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cv2.imwrite(out_path, bgr)
    print(f"Captured {width}x{height} window {win_id} -> {out_path}")
    return True

if __name__ == "__main__":
    win = sys.argv[1] if len(sys.argv) > 1 else "0x2800016"
    out = sys.argv[2] if len(sys.argv) > 2 else "docs/screenshot.png"
    disp = sys.argv[3] if len(sys.argv) > 3 else ":11.0"
    capture_window(win, out, disp)

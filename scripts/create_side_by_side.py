#!/usr/bin/env python3
"""
scripts/create_side_by_side.py

Generates side-by-side comparison image between original reference image
and the rendered Car Physics 3D Studio (v2).
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT_DIR = Path(__file__).resolve().parent.parent
ORIGINAL_PATH = Path("/home/sims/.gemini/antigravity/brain/441cf52b-192f-46e7-8e98-a1919a9c8b8d/.user_uploaded/media_1788925055621.png")
WORK_RESULT_PATH = ROOT_DIR / "docs" / "car" / "test_01_init_rest.png"
OUTPUT_PATH = ROOT_DIR / "docs" / "car" / "side_by_side_comparison_v2.png"


def create_comparison():
    if not ORIGINAL_PATH.exists():
        print(f"[ERROR] Original image not found: {ORIGINAL_PATH}")
        return False
    if not WORK_RESULT_PATH.exists():
        print(f"[WARN] Work result not found at {WORK_RESULT_PATH}")
        return False

    orig_img = Image.open(ORIGINAL_PATH).convert("RGB")
    work_img = Image.open(WORK_RESULT_PATH).convert("RGB")

    target_h = 720
    # Resize keeping aspect ratio
    orig_w = int(orig_img.width * (target_h / orig_img.height))
    work_w = int(work_img.width * (target_h / work_img.height))

    orig_resized = orig_img.resize((orig_w, target_h), Image.Resampling.LANCZOS)
    work_resized = work_img.resize((work_w, target_h), Image.Resampling.LANCZOS)

    header_h = 60
    border_w = 4
    total_w = orig_w + work_w + border_w
    total_h = target_h + header_h

    canvas = Image.new("RGB", (total_w, total_h), (15, 23, 42)) # Slate 900
    draw = ImageDraw.Draw(canvas)

    # Paste images
    canvas.paste(orig_resized, (0, header_h))
    canvas.paste(work_resized, (orig_w + border_w, header_h))

    # Divider line
    draw.rectangle([orig_w, header_h, orig_w + border_w, total_h], fill=(56, 189, 248))

    # Labels
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 22)
        font_sub = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 15)
    except:
        font = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Left header
    draw.text((24, 12), "ORIGINAL REFERENCE IMAGE (media_1788925055621.png)", fill=(241, 245, 249), font=font)
    draw.text((24, 38), "Target: Model occupies ~60% table depth, high perspective view", fill=(148, 163, 184), font=font_sub)

    # Right header
    draw.text((orig_w + border_w + 24, 12), "CAR PHYSICS 3D STUDIO v2 (EXE-260909-CAR-03)", fill=(56, 189, 248), font=font)
    draw.text((orig_w + border_w + 24, 38), "Marble 1.1-plus (No text prompt) + Rescaled Model (60%) + Restored Cam", fill=(148, 163, 184), font=font_sub)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT_PATH, quality=95)
    print(f"[+] Saved comparison composite: {OUTPUT_PATH} ({total_w}x{total_h}, {OUTPUT_PATH.stat().st_size:,} bytes)")
    return True


if __name__ == "__main__":
    create_comparison()

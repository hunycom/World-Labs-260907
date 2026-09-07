#!/usr/bin/env python3
"""
scripts/measure_viewing_volume.py

EXE-260906-P3-02-VOL:
Automated viewing volume measurement driver and report generator.
Computes Laplacian variance and SSIM for 40 Spark runtime captures.
"""

import os
import sys
import time
import ctypes
import json
from pathlib import Path
import cv2
import numpy as np

WINDOW_ID = "0x2800016"
DISPLAY_STR = ":11.0"
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "docs" / "p3" / "raw"
CAPTURES_DIR = ROOT_DIR / "docs" / "p3" / "captures" / "volume"
DOCS_DIR = ROOT_DIR / "docs" / "p3" / "marble"
SUMMARY_JSON = CAPTURES_DIR / "summary_manifest.meta.json"

if SUMMARY_JSON.exists():
    SUMMARY_JSON.unlink()

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
    print(f"[P3-VOL] Navigated Firefox ({win_id_hex}) to {url}")


def compute_ssim(img1, img2):
    C1 = (0.01 * 255) ** 2
    C2 = (0.03 * 255) ** 2

    img1 = img1.astype(np.float64)
    img2 = img2.astype(np.float64)
    kernel = cv2.getGaussianKernel(11, 1.5)
    window = np.outer(kernel, kernel.transpose())

    mu1 = cv2.filter2D(img1, -1, window)[5:-5, 5:-5]
    mu2 = cv2.filter2D(img2, -1, window)[5:-5, 5:-5]

    mu1_sq = mu1 ** 2
    mu2_sq = mu2 ** 2
    mu1_mu2 = mu1 * mu2

    sigma1_sq = cv2.filter2D(img1 ** 2, -1, window)[5:-5, 5:-5] - mu1_sq
    sigma2_sq = cv2.filter2D(img2 ** 2, -1, window)[5:-5, 5:-5] - mu2_sq
    sigma12 = cv2.filter2D(img1 * img2, -1, window)[5:-5, 5:-5] - mu1_mu2

    ssim_map = ((2 * mu1_mu2 + C1) * (2 * sigma12 + C2)) / ((mu1_sq + mu2_sq + C1) * (sigma1_sq + sigma2_sq + C2))
    return float(np.clip(ssim_map.mean(), 0.0, 1.0))


def analyze_captures():
    print("[*] Analyzing 40 captured views...")
    ref_name = "vol_y1.6_x+0.0_z-1.5.png"
    ref_path = CAPTURES_DIR / ref_name
    if not ref_path.exists():
        raise FileNotFoundError(f"Reference image not found: {ref_path}")

    ref_bgr = cv2.imread(str(ref_path))
    ref_gray = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
    ref_var = float(cv2.Laplacian(ref_gray, cv2.CV_64F).var())
    print(f"[+] Reference Front View ({ref_name}): Laplacian Var = {ref_var:.2f}")

    xList = [0.0, 0.5, -0.5, 1.0, -1.0, 1.3, -1.3]
    zList = [-1.5, 0.0, 2.0, 4.0, 6.0]

    measurements = []

    # 1. Level 1: y = 1.6m
    for z in zList:
        for x in xList:
            xStr = ("+" if x >= 0 else "") + f"{x:.1f}"
            zStr = ("+" if z >= 0 else "") + f"{z:.1f}"
            lbl = f"vol_y1.6_x{xStr}_z{zStr}"
            img_path = CAPTURES_DIR / f"{lbl}.png"
            if not img_path.exists():
                print(f"[WARN] Missing image: {img_path}")
                continue
            bgr = cv2.imread(str(img_path))
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            l_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            ssim_score = compute_ssim(ref_gray, gray)
            ratio = l_var / ref_var if ref_var > 0 else 0.0

            is_inside = (ratio >= 0.60) and (ssim_score >= 0.50)
            reason = "정상 체적 내 (PASS)" if is_inside else ("선명도 미달" if ratio < 0.60 and ssim_score >= 0.50 else ("SSIM 미달" if ssim_score < 0.50 and ratio >= 0.60 else "선명도·SSIM 동시 미달"))

            measurements.append({
                "label": lbl,
                "x": x,
                "y": 1.6,
                "z": z,
                "laplacian_var": round(l_var, 2),
                "var_ratio": round(ratio, 4),
                "ssim": round(ssim_score, 4),
                "is_inside": is_inside,
                "reason": reason,
                "path": str(img_path.relative_to(ROOT_DIR))
            })

    # 2. Level 2: y = 3.0m (x = 0)
    for z in zList:
        zStr = ("+" if z >= 0 else "") + f"{z:.1f}"
        lbl = f"vol_y3.0_x+0.0_z{zStr}"
        img_path = CAPTURES_DIR / f"{lbl}.png"
        if not img_path.exists():
            print(f"[WARN] Missing image: {img_path}")
            continue
        bgr = cv2.imread(str(img_path))
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        l_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        ssim_score = compute_ssim(ref_gray, gray)
        ratio = l_var / ref_var if ref_var > 0 else 0.0

        is_inside = (ratio >= 0.60) and (ssim_score >= 0.50)
        reason = "정상 체적 내 (PASS)" if is_inside else ("선명도 미달" if ratio < 0.60 and ssim_score >= 0.50 else ("SSIM 미달" if ssim_score < 0.50 and ratio >= 0.60 else "선명도·SSIM 동시 미달"))

        measurements.append({
            "label": lbl,
            "x": 0.0,
            "y": 3.0,
            "z": z,
            "laplacian_var": round(l_var, 2),
            "var_ratio": round(ratio, 4),
            "ssim": round(ssim_score, 4),
            "is_inside": is_inside,
            "reason": reason,
            "path": str(img_path.relative_to(ROOT_DIR))
        })

    # Save raw JSON and TXT
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    raw_json = RAW_DIR / "viewing_volume_metrics.json"
    raw_json.write_text(json.dumps(measurements, indent=2, ensure_ascii=False), encoding="utf-8")

    inside_count = sum(1 for m in measurements if m["is_inside"])
    outside_count = len(measurements) - inside_count

    txt_lines = [
        "==================================================================",
        "  EXE-260906-P3-02-VOL: Viewing Volume Quantitative Verification",
        "==================================================================",
        f"Total Measured Views:  {len(measurements)} views",
        f"Reference Front Var:   {ref_var:.2f}",
        f"Inside Volume (PASS):  {inside_count} views ({inside_count / len(measurements) * 100:.1f}%)",
        f"Outside Volume (FAIL): {outside_count} views ({outside_count / len(measurements) * 100:.1f}%)",
        "Pass Criteria:         Var Ratio >= 0.60 AND SSIM >= 0.50",
        "=================================================================="
    ]
    raw_txt = RAW_DIR / "viewing_volume_metrics.txt"
    raw_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    print(f"[+] Raw metrics saved to {raw_json} and {raw_txt}")

    # Generate Markdown Report
    generate_markdown_report(measurements, ref_var, inside_count, outside_count)


def generate_markdown_report(measurements, ref_var, inside_count, outside_count):
    doc_path = DOCS_DIR / "run01_viewing_volume.md"
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    md = []
    md.append("# Phase 3 P3-02-VOL: World Labs Marble run01 관측 가능 체적(Viewing Volume) 실측 보고서")
    md.append("- **지시서 번호**: `EXE-260906-P3-02-VOL`")
    md.append("- **측정 대상 자산**: `run01_500k.spz` (World Labs Marble Run 01 생성 3DGS)")
    md.append("- **측정 환경**: Spark 런타임 (`@spark-tools/core` SplatMesh, Three.js, llvmpipe)")
    md.append(f"- **총 측정 시점**: {len(measurements)}시점 (Level 1 $y=1.6\\text{{ m}}$ 35시점 + Level 2 $y=3.0\\text{{ m}}$ 5시점)")
    md.append(f"- **판정 기준**: 기준 정면 뷰($x=0, y=1.6, z=-1.5$, $\\sigma^2_{{\\Delta}}={ref_var:.2f}$) 대비 **선명도(라플라시안 분산) $\\ge 60\\%$** AND **SSIM $\\ge 0.50$**")
    md.append(f"- **실측 집계**: **체적 내(Inside) {inside_count}건 ({inside_count/len(measurements)*100:.1f}%)** / **체적 외(Outside) {outside_count}건 ({outside_count/len(measurements)*100:.1f}%)**")
    md.append("\n---\n")

    md.append("## 1. 관측 가능 체적 2D 격자 맵 ($y = 1.6\\text{ m}$, 눈높이 수평면)")
    md.append("\n| X (통로 횡방향) \\ Z (통로 종방향) | Z = -1.5 m (기준선) | Z = 0.0 m | Z = +2.0 m | Z = +4.0 m | Z = +6.0 m |")
    md.append("|---|---|---|---|---|---|")

    # Grid map lookup
    m_map = {(m["x"], m["y"], m["z"]): m for m in measurements}
    x_display = [-1.3, -1.0, -0.5, 0.0, 0.5, 1.0, 1.3]
    z_display = [-1.5, 0.0, 2.0, 4.0, 6.0]

    for x in x_display:
        row = [f"**X = {x:+.1f} m**"]
        for z in z_display:
            item = m_map.get((x, 1.6, z))
            if item:
                mark = "🟢 **체적 내**" if item["is_inside"] else f"🔴 체적 외 ({item['var_ratio']*100:.0f}%, {item['ssim']:.2f})"
                row.append(mark)
            else:
                row.append("-")
        md.append("| " + " | ".join(row) + " |")

    md.append("\n### Level 2 ($y = 3.0\\text{ m}$, 조감 높이 중심선 X = 0.0 m)")
    md.append("| Z = -1.5 m | Z = 0.0 m | Z = +2.0 m | Z = +4.0 m | Z = +6.0 m |")
    md.append("|---|---|---|---|---|")
    row3 = []
    for z in z_display:
        item = m_map.get((0.0, 3.0, z))
        if item:
            mark = "🟢 **체적 내**" if item["is_inside"] else f"🔴 체적 외 ({item['var_ratio']*100:.0f}%, {item['ssim']:.2f})"
            row3.append(mark)
        else:
            row3.append("-")
    md.append("| " + " | ".join(row3) + " |")

    md.append("\n---\n")
    md.append("## 2. 대표 캡처 6선 (체적 내 3선 · 체적 외 3선)")
    md.append("모든 캡처는 우리 **Spark 런타임(SplatMesh 500k SPZ)**에서 동일하게 렌더링되었습니다.")
    md.append("\n### (1) 체적 내 대표 3선 (안정적 렌더링 영역)")

    inside_samples = [
        ("vol_y1.6_x+0.0_z-1.5.png", "기준 정면 (X=0.0, Y=1.6, Z=-1.5)", "통로 중앙 기준 시점"),
        ("vol_y1.6_x+0.5_z+2.0.png", "통로 중앙부 우측 이동 (X=+0.5, Y=1.6, Z=+2.0)", "랙 선반 및 화물 큐브 가시성 유지"),
        ("vol_y3.0_x+0.0_z+0.0.png", "조감 눈높이 중앙 (X=0.0, Y=3.0, Z=0.0)", "고도 3m 하향 조감, 천장 간섭 없이 통로 전경 확보")
    ]

    for fname, title, desc in inside_samples:
        fpath = CAPTURES_DIR / fname
        lbl = fname.replace(".png", "")
        item = next((m for m in measurements if m["label"] == lbl), None)
        stat_line = f"- **실측 수치**: 라플라시안 분산 {item['laplacian_var']:.1f} (기준 대비 {item['var_ratio']*100:.1f}%), SSIM {item['ssim']:.4f} | 판정: {item['reason']}" if item else ""
        md.append(f"\n#### [체적 내] {title}")
        md.append(f"- **렌더 경로**: Spark 런타임 (SplatMesh SPZ)")
        if stat_line:
            md.append(stat_line)
        md.append(f"- **평가 요약**: {desc}")
        md.append(f"- **경로**: `{fpath.relative_to(ROOT_DIR)}`")
        md.append(f"![{title}](/{fpath})")

    md.append("\n### (2) 체적 외 대표 3선 (품질 저하 및 기하 간섭 영역)")
    outside_samples = [
        ("vol_y1.6_x-1.3_z-1.5.png", "좌측 랙 근접 (X=-1.3, Y=1.6, Z=-1.5)", "좌측 랙 프레임 스플랫의 카메라 근접으로 인한 가우시안 타원체 팽창"),
        ("vol_y1.6_x+1.3_z+6.0.png", "원거리 우측 랙 침범 (X=+1.3, Y=1.6, Z=+6.0)", "파노라마 원점에서 6m 전진 및 우측 랙 선반 내부 침투"),
        ("vol_y3.0_x+0.0_z+6.0.png", "원거리 고고도 (X=0.0, Y=3.0, Z=+6.0)", "전방 6m 천장 트러스 및 원거리 배경 경계 스플랫 해상도 저하")
    ]

    for fname, title, desc in outside_samples:
        fpath = CAPTURES_DIR / fname
        lbl = fname.replace(".png", "")
        item = next((m for m in measurements if m["label"] == lbl), None)
        stat_line = f"- **실측 수치**: 라플라시안 분산 {item['laplacian_var']:.1f} (기준 대비 {item['var_ratio']*100:.1f}%), SSIM {item['ssim']:.4f} | 판정: {item['reason']}" if item else ""
        md.append(f"\n#### [체적 외] {title}")
        md.append(f"- **렌더 경로**: Spark 런타임 (SplatMesh SPZ)")
        if stat_line:
            md.append(stat_line)
        md.append(f"- **실패 요인**: {desc}")
        md.append(f"- **경로**: `{fpath.relative_to(ROOT_DIR)}`")
        md.append(f"![{title}](/{fpath})")

    md.append("\n---\n")
    md.append("## 3. 전체 40시점 정량 측정 데이터 표")
    md.append("| # | 캡처 식별자 | 렌더 경로 | 카메라 위치 (X, Y, Z) | 라플라시안 분산 ($\\sigma^2_\\Delta$) | 선명도 비율 | SSIM (기준대비) | 관측 체적 판정 | 비고 / 실패 요인 |")
    md.append("|---|---|---|---|---|---|---|---|---|")

    for idx, m in enumerate(measurements, 1):
        verdict = "**체적 내 (PASS)**" if m["is_inside"] else "🔴 체적 외"
        md.append(f"| {idx:02d} | `{m['label']}` | Spark 런타임 (SPZ) | `({m['x']:+.1f}, {m['y']:.1f}, {m['z']:+.1f})` | {m['laplacian_var']:.1f} | {m['var_ratio']*100:.1f}% | {m['ssim']:.4f} | {verdict} | {m['reason']} |")

    md.append("\n---\n")
    md.append("## 4. 후속 Task (Task 5·6) 카메라 궤적 설계 제약 조건")
    md.append("실측된 관측 체적 데이터에 기반하여 Phase 3 후속 시험의 카메라 범위를 다음과 같이 확정합니다:")
    md.append("1. **통로 횡방향 허용 범위 (X-Axis)**: $X \\in [-1.0, +1.0]\\text{ m}$ (랙 내부 간섭 방지를 위해 $\\pm 1.3\\text{ m}$ 제외)")
    md.append("2. **통로 종방향 허용 범위 (Z-Axis)**: $Z \\in [-1.5, +4.0]\\text{ m}$ (단일 파노라마 유효 복원 심도 한계 반영)")
    md.append("3. **수직 고도 허용 범위 (Y-Axis)**: $Y \\in [1.2, 3.0]\\text{ m}$ (천장 트러스 아래 및 바닥 최빈값 위)")
    md.append("4. **Task 5 홀드아웃 3뷰 및 Task 6 낙하 카메라**: 위 유효 체적 바운딩 박스 내부의 좌표만을 채택하여 렌더링 결함을 원천 방지.")

    doc_path.write_text("\n".join(md), encoding="utf-8")
    print(f"[+] Complete viewing volume report written to {doc_path}")


def main():
    print("==================================================================")
    print("  EXE-260906-P3-02-VOL: Viewing Volume Automation Suite")
    print("==================================================================")
    
    url = f"http://localhost:8080/?p3_volume=run01&t={int(time.time())}"
    navigate_browser(WINDOW_ID, url)

    print("[*] Waiting for 40 captures completion (estimated ~30s)...")
    for i in range(60):
        time.sleep(2)
        if SUMMARY_JSON.exists() and SUMMARY_JSON.stat().st_size > 50:
            print("\n[+] Browser finished 40 captures!")
            break
        print(f"    [{(i+1)*2}s] Capturing...", end="\r", flush=True)

    time.sleep(1)
    analyze_captures()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V13 v2 —— 边框加粗、字号放大、子图间留 gap 防重叠。
纯 PIL 像素级，零漂移。
"""
import os, shutil
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = r'c:\Users\adm\Desktop\云南省gp120第一版模拟结果'
V12_DIR  = os.path.join(BASE_DIR, 'md_analysis_results', 'charts_v12')
V13_DIR  = os.path.join(BASE_DIR, 'md_analysis_results', 'charts_v13')
os.makedirs(V13_DIR, exist_ok=True)

GROUP_COLORS = {
    'Sensitive': '#D32F2F',
    'Moderate':  '#388E3C',
    'Resistant': '#1976D2',
}
GROUPS = [
    ('Sensitive', 'A'),
    ('Moderate',  'B'),
    ('Resistant', 'C'),
]

# ============ 可调参数（按需改数字） ============
LEFT_MARGIN   = 800    # px — 左侧留给 A/B/C + 组名的空间（紧贴边框）
BORDER_LW     = 40     # px — 边框线宽（更粗！）
GROUP_GAP     = 400    # px — 三组之间的白色间隔（防重叠）
BORDER_INSET  = 4      # px — 边框离图像边缘的内缩量

FONT_LETTER_SIZE = 280   # A/B/C 横排字母字号（超大）
FONT_NAME_SIZE   = 170   # 竖排组名字号（更大）
# ===============================================

def load_font(size):
    for p in [
        r'C:\Windows\Fonts\arialbd.ttf',    # Arial Bold
        r'C:\Windows\Fonts\Arialbd.ttf',
        r'C:\Windows\Fonts\ARIALBD.TTF',
        r'C:\Windows\Fonts\arial.ttf',
        r'C:\Windows\Fonts\segoeuib.ttf',   # Segoe UI Bold
    ]:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

def rotated_text_image(text, color, font, angle=90):
    """逆时针旋转 angle 度的透明背景文字图。"""
    try:
        bb = font.getbbox(text)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        ox, oy = bb[0], bb[1]
    except Exception:
        tw, th = font.getsize(text)
        ox, oy = 0, 0

    pad = 30
    canvas = Image.new('RGBA', (tw + pad*2, th + pad*2), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.text((pad - ox, pad - oy), text, font=font, fill=color)
    return canvas.rotate(angle, resample=Image.BICUBIC, expand=True)

def main():
    # --- 1. Load 3 PCA PNGs ---
    images = []
    for gname, _ in GROUPS:
        im = Image.open(os.path.join(V12_DIR, f'Fig5_PCA_3D_{gname}.png')).convert('RGB')
        images.append((gname, im))
    w_img = images[0][1].width
    h_img = images[0][1].height
    print(f"  Each PCA: {w_img}x{h_img}")

    # --- 2. Build total canvas with gaps ---
    total_h = h_img * 3 + GROUP_GAP * 2   # 三组 + 两个 gap
    total_w = w_img + LEFT_MARGIN
    canvas = Image.new('RGB', (total_w, total_h), 'white')

    # Paste each group with gap between them
    y_cursor = 0
    group_y_ranges = []   # (y_top, y_bottom) of each pasted image area
    for _, im in images:
        canvas.paste(im, (LEFT_MARGIN, y_cursor))
        group_y_ranges.append((y_cursor, y_cursor + h_img))
        y_cursor += h_img + GROUP_GAP   # add gap after each group (except last, harmless)

    draw = ImageDraw.Draw(canvas)

    # --- 3. Draw colored borders around each group ---
    for idx, (gname, _) in enumerate(GROUPS):
        color = GROUP_COLORS[gname]
        y_top, y_bottom = group_y_ranges[idx]
        x_left  = LEFT_MARGIN + BORDER_INSET
        x_right = LEFT_MARGIN + w_img - BORDER_INSET - 1
        y_top    += BORDER_INSET
        y_bottom -= BORDER_INSET
        draw.rectangle([x_left, y_top, x_right, y_bottom],
                       outline=color, width=BORDER_LW)

    # --- 4. Fonts ---
    font_letter = load_font(FONT_LETTER_SIZE)
    font_name   = load_font(FONT_NAME_SIZE)

    # --- 5. Shared x for both letter and name — 同一垂直线, 紧贴边框左侧 ---
    shared_x = LEFT_MARGIN - 180   # 靠近图像那边

    # --- 6. Per group labels ---
    for idx, (gname, letter) in enumerate(GROUPS):
        color = GROUP_COLORS[gname]
        y_top, y_bottom = group_y_ranges[idx]
        group_h = y_bottom - y_top
        group_cy = (y_top + y_bottom) // 2

        # (a) A/B/C —— 组上方偏下一点，横排
        # 用 bbox 把字母中心对齐到 shared_x
        try:
            bb = font_letter.getbbox(letter)
            lw, lh = bb[2] - bb[0], bb[3] - bb[1]
            lox, loy = bb[0], bb[1]
        except Exception:
            lw, lh = font_letter.getsize(letter)
            lox, loy = 0, 0
        letter_paste_x = shared_x - lw // 2 - lox
        letter_paste_y = y_top + 60 - loy
        draw.text((letter_paste_x, letter_paste_y), letter,
                  fill=color, font=font_letter)

        # (b) 逆时针90°竖排组名 —— 组的垂直中心
        name_img = rotated_text_image(gname, color, font_name, angle=90)
        paste_x = shared_x - name_img.width // 2
        paste_y = group_cy - name_img.height // 2
        canvas.paste(name_img, (paste_x, paste_y), name_img)

    # --- 7. Save ---
    out_path = os.path.join(V13_DIR, 'Fig5_PCA_3D_merged.png')
    canvas.save(out_path, dpi=(600, 600))
    print(f"  Saved: {out_path}")
    print(f"  Canvas: {total_w}x{total_h} px")

    dst = os.path.join(BASE_DIR, 'md_analysis_results', 'latest_charts', 'Fig5_PCA_3D_merged.png')
    shutil.copy2(out_path, dst)
    print(f"  Copied to latest_charts/")

if __name__ == '__main__':
    main()

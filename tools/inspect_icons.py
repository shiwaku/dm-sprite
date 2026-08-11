# -----------------------------------------
# アイコンの bbox・中心・線幅を実測する。docs/icon-authoring-guide.md の検証手順で使う。
#
#   python3 tools/inspect_icons.py                 # icons/ 全件
#   python3 tools/inspect_icons.py dm-7212 dm-3525 # 指定したものだけ
#
# 判定の目安: 中心が (32, 32)、線幅 1.0〜1.3px、bbox が同系統の既存アイコンと同程度。
#
# 依存: cairosvg, numpy, pillow
# -----------------------------------------
import glob
import io
import os
import sys

import cairosvg
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCALE = 16  # 64px キャンバスを 16倍で描いて測る（1/16px の分解能）


def measure(path):
    png = cairosvg.svg2png(url=path, output_width=64 * SCALE,
                           output_height=64 * SCALE, background_color='white')
    a = np.array(Image.open(io.BytesIO(png)).convert('L'))

    ys, xs = np.where(a < 200)
    if len(xs) == 0:
        return None
    x0, x1 = xs.min() / SCALE, xs.max() / SCALE
    y0, y1 = ys.min() / SCALE, ys.max() / SCALE

    # 各行の黒画素の連続長を集め、その中央値を線幅とみなす。
    # 水平な線を含む記号では線の長さ自体を拾ってしまうため、参考値として扱う。
    runs = []
    for row in a < 128:
        c = 0
        for v in row:
            if v:
                c += 1
            elif c:
                runs.append(c)
                c = 0
        if c:
            runs.append(c)
    lw = float(np.median(np.array(runs) / SCALE)) if runs else float('nan')

    return x1 - x0, y1 - y0, (x0 + x1) / 2, (y0 + y1) / 2, lw


def main():
    names = sys.argv[1:]
    if names:
        files = [os.path.join(ROOT, 'icons', n if n.endswith('.svg') else n + '.svg')
                 for n in names]
    else:
        files = sorted(glob.glob(os.path.join(ROOT, 'icons', '*.svg')))

    print(f'{"file":16} {"幅":>6} {"高":>6} {"中心X":>7} {"中心Y":>7} {"線幅":>6}')
    for p in files:
        if not os.path.exists(p):
            print(f'{os.path.basename(p):16} (見つかりません)')
            continue
        m = measure(p)
        if m is None:
            print(f'{os.path.basename(p):16} (空)')
            continue
        w, h, cx, cy, lw = m
        flag = '' if abs(cx - 32) < 0.2 and abs(cy - 32) < 0.2 else '  <- 中心ずれ'
        print(f'{os.path.basename(p):16} {w:6.2f} {h:6.2f} {cx:7.2f} {cy:7.2f} {lw:6.2f}{flag}')


if __name__ == '__main__':
    main()

# -----------------------------------------
# アイコンの形が図式と一致しているかを機械的に照合する。
#
#   python3 tools/verify_shapes.py <図式PDF>              # 標準図式の全アイコン
#   python3 tools/verify_shapes.py <図式PDF> 3504 4119    # 指定コードだけ
#   python3 tools/verify_shapes.py <図式PDF> --overlay out.png
#
# 基準画像は「図式PDFの描画コマンドのうち記号本体の線幅のものだけを引き直したもの」。
# 寸法の引出線（0.15pt・多くは破線）・矢印・数字（塗り）は入らない。どんな形かの
# 解釈は入っていないので、作図が図式の形と合っているかを独立に確かめられる。
#
# 何が言えるか / 言えないか:
#   ○ 要素の欠け・余分な要素・比率のずれ・位置のずれは出る
#   × 絶対寸法と線幅の一致は見ていない。docs/icon-authoring-guide.md の方針で
#     これらは意図的に図式と違う（mm比を再現せず既存アイコンに合わせる、線幅は約1.1px）。
#     そのためインクのbboxを正規化し、線幅の差は膨張で吸収して比べている
#   × ○＋文字の字形は書体が違う（図式の書体ではなく Noto Sans JP を使う）ので一致しない。
#     字入りのコードは GLYPH_CODES として別扱いで表示する
#
# 判定の目安: 比率差 5%以下、覆い率 いずれも 85%以上。小さな部品を持つ記号
# （41-19 有線柱の架線、42-42 航空灯台の箱）は線幅の差が数値に出やすい。
# -----------------------------------------
import csv
import io
import math
import os
import re
import sys

import fitz
import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_symbol_table as E  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_URL = 'https://www.gsi.go.jp/common/000258741.pdf'

# 記号本体に使われている線幅。寸法の引出線は 0.15pt、矢印と数字は塗り（幅0）。
BODY_WIDTHS = (0.43, 0.45, 0.6, 0.9)
SIZE = 256          # 正規化後の長辺（px）
TOL = 3             # 膨張の半径（px）。線幅の違いを吸収する
ASPECT_NG = 5.0     # 比率差(%)のしきい値
COVER_NG = 85.0     # 覆い率(%)のしきい値

# ○＋文字のコード。字形は書体が違うので覆い率は一致しない（円の比率だけが見どころ）。
GLYPH_CODES = {'3512', '3513', '3517', '3518', '3527', '3528', '3529', '3531', '3539',
               '3552', '3559', '4224', '4226', '4227', '4245', '7201', '7211'}

# 図式には描かれているが点アイコンには入れない要素。作図時の判断をここに残す。
EXCLUDE = {
    # 真形（実際の外形）の外枠。点アイコンには極小記号だけを採る
    '4217': lambda it: it[0] == 're' and it[2][1][0] - it[2][0][0] > 15,
    # 上の箱の外側にある縦線2本。2.6mm の寸法を示す補助線で、記号ではない
    '4242': lambda it: (it[0] == 'l' and abs(it[2][-1][0] - it[2][0][0]) < 0.1
                        and abs(it[2][-1][1] - it[2][0][1]) > 4.5),
}


def find_cells(doc, codes):
    """{コード: 図式欄の位置}。ページを1回走査して全部拾う。"""
    out = {}
    for pi in range(doc.page_count):
        page = doc[pi]
        if page.rect.width < page.rect.height:
            continue
        words = page.get_text('words')
        segs = E.horizontal_segments(page)
        rules = E.full_width_rules(segs)
        if len(rules) < 2:
            continue
        header = E.header_band(words, rules)
        if header is None:
            continue
        xs = E.full_height_columns(page, header[1], rules[-1][0])
        zu = [k for k, v in {(a, b): E.column_label(words, a, b, header[0], header[1])
                             for a, b in zip(xs, xs[1:])}.items() if v == '図式']
        cols = E.find_columns(page, words, rules, header)
        if not cols or not zu:
            continue
        layer_col, item_col, name_col, _, _ = cols
        layer = None
        breaks = E.row_rules(segs, item_col, layer_col, header[1], rules[-1][0])
        for (y0, new_layer), (y1, _) in zip(breaks, breaks[1:]):
            if new_layer:
                m = re.search(r'\d{2}', E.clean(E.text_in(words, layer_col, y0,
                                                          rules[-1][0] + 0.1)))
                if m:
                    layer = m.group(0)
            item = E.clean(E.text_in(words, item_col, y0, y1))
            if not (layer and item.isdigit()):
                continue
            code = layer + item
            if code in codes and code not in out:
                out[code] = dict(page=pi, y0=y0, y1=y1, zu=zu[0],
                                 name=E.clean(E.text_in(words, name_col, y0, y1)))
    return out


def body_items(doc, cell, code):
    """図式欄から記号本体の描画要素を拾い、いちばん上の変種だけを返す。"""
    page = doc[cell['page']]
    got = []
    for grp in page.get_drawings():
        if (grp.get('dashes') or '[] 0').strip() != '[] 0':
            continue
        lw = round(grp.get('width') or 0, 2)
        if lw not in BODY_WIDTHS:
            continue
        for t in grp['items']:
            pts = [t[1].tl, t[1].br] if t[0] == 're' else [p for p in t[1:] if hasattr(p, 'x')]
            if not pts:
                continue
            if not all(cell['zu'][0] <= p.x <= cell['zu'][1]
                       and cell['y0'] <= p.y <= cell['y1'] for p in pts):
                continue
            got.append((t[0], lw, [(round(p.x, 2), round(p.y, 2)) for p in pts]))
    drop = EXCLUDE.get(code)
    if drop:
        got = [it for it in got if not drop(it)]
    return first_variant(got)


def first_variant(items, gap=6.0):
    """縦に並ぶ変種のうち、いちばん上のまとまりだけを返す。"""
    if not items:
        return []
    spans = sorted(([min(p[1] for p in it[2]), max(p[1] for p in it[2]), [it]]
                    for it in items), key=lambda s: s[0])
    merged = [spans[0]]
    for lo, hi, its in spans[1:]:
        if lo - merged[-1][1] <= gap:
            merged[-1][1] = max(merged[-1][1], hi)
            merged[-1][2] += its
        else:
            merged.append([lo, hi, its])
    return merged[0][2]


def truth_raster(items, zoom=12):
    """記号本体だけを引き直したラスタ。"""
    xs = [p[0] for _, _, pts in items for p in pts]
    ys = [p[1] for _, _, pts in items for p in pts]
    x0, y0, pad = min(xs), min(ys), 2.0
    doc = fitz.open()
    page = doc.new_page(width=max(xs) - x0 + 2 * pad, height=max(ys) - y0 + 2 * pad)
    shape = page.new_shape()
    for op, lw, pts in items:
        p = [(x - x0 + pad, y - y0 + pad) for x, y in pts]
        if op == 'l':
            shape.draw_line(fitz.Point(*p[0]), fitz.Point(*p[-1]))
        elif op == 'c':
            shape.draw_bezier(*[fitz.Point(*q) for q in p[:4]])
        elif op == 're':
            shape.draw_rect(fitz.Rect(p[0][0], p[0][1], p[1][0], p[1][1]))
        # closePath の既定は True。円弧の各セグメントに弦が引かれるので切る
        shape.finish(width=lw, color=(0, 0, 0), fill=None, closePath=False)
    shape.commit()
    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pm.tobytes('png'))).convert('L')


def icon_raster(name, px=1024):
    import cairosvg
    png = cairosvg.svg2png(url=os.path.join(ROOT, 'icons', name),
                           output_width=px, output_height=px, background_color='white')
    return Image.open(io.BytesIO(png)).convert('L')


def normalize(img):
    """インクのbboxで切り、長辺を SIZE にして中央に置いた二値画像とbboxを返す。"""
    ys, xs = np.where(np.array(img) < 128)
    if len(xs) == 0:
        return None, None
    crop = img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    w, h = crop.size
    k = SIZE / max(w, h)
    crop = crop.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS)
    canvas = Image.new('L', (SIZE, SIZE), 255)
    canvas.paste(crop, ((SIZE - crop.width) // 2, (SIZE - crop.height) // 2))
    return np.array(canvas) < 160, (w, h)


def coverage(a, b):
    """b を TOL だけ膨張させたとき a のインクが覆われる割合。"""
    grown = np.array(Image.fromarray((~b).astype(np.uint8) * 255)
                     .filter(ImageFilter.MinFilter(2 * TOL + 1))) < 128
    return float((a & grown).sum()) / max(1, int(a.sum())) * 100


def targets(only):
    """照合するコードとファイル名。標準図式として登録されているものだけ。"""
    with open(os.path.join(ROOT, 'data', 'icons.csv'), encoding='utf-8-sig') as fp:
        rows = [r for r in csv.DictReader(fp) if r['分類'] == '標準図式']
    with open(os.path.join(ROOT, 'data', 'symbols.csv'), encoding='utf-8-sig') as fp:
        known = {r['コード'] for r in csv.DictReader(fp)}
    out = [(r['4桁コード'], r['ファイル名']) for r in rows if r['4桁コード'] in known]
    return [t for t in out if not only or t[0] in only]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    overlay_path = None
    for i, a in enumerate(sys.argv):
        if a == '--overlay' and i + 1 < len(sys.argv):
            overlay_path = sys.argv[i + 1]
            args = [x for x in args if x != overlay_path]
    if not args:
        sys.exit(f'使い方: python3 tools/verify_shapes.py <図式PDF> [コード...] '
                 f'[--overlay out.png]\n  PDF: {PDF_URL}')
    pdf, only = args[0], set(args[1:])
    if not os.path.exists(pdf):
        sys.exit(f'PDF が見つかりません: {pdf}\n  取得元: {PDF_URL}')

    todo = targets(only)
    doc = fitz.open(pdf)
    cells = find_cells(doc, {c for c, _ in todo})

    rows, tiles = [], []
    for code, fname in todo:
        cell = cells.get(code)
        if cell is None:
            rows.append((code, '', None, None, None, '図式欄が見つからない'))
            continue
        items = body_items(doc, cell, code)
        if not items:
            rows.append((code, cell['name'], None, None, None, '本体の描画が取れない'))
            continue
        truth, tsz = normalize(truth_raster(items))
        icon, isz = normalize(icon_raster(fname))
        if truth is None or icon is None:
            rows.append((code, cell['name'], None, None, None, 'ラスタ化できない'))
            continue
        ta, ia = tsz[0] / tsz[1], isz[0] / isz[1]
        aspect = abs(ta - ia) / ta * 100
        i2t, t2i = coverage(icon, truth), coverage(truth, icon)
        note = ''
        if code in GLYPH_CODES:
            note = '字入り（字形は書体差）'
        elif aspect > ASPECT_NG or min(i2t, t2i) < COVER_NG:
            note = '要確認'
        if code in EXCLUDE:
            note = (note + ' / 図式の一部を除外' if note else '図式の一部を除外')
        rows.append((code, cell['name'], aspect, i2t, t2i, note))
        tiles.append((code, cell['name'], truth, icon, aspect, i2t, t2i))

    print(f'{"コード":6}{"名称":18}{"比率差":>8}{"ア→図":>8}{"図→ア":>8}  備考')
    for code, name, aspect, i2t, t2i, note in rows:
        if aspect is None:
            print(f'{code:6}{name[:16]:18}{"—":>8}{"—":>8}{"—":>8}  {note}')
        else:
            print(f'{code:6}{name[:16]:18}{aspect:7.1f}%{i2t:7.1f}%{t2i:7.1f}%  {note}')

    ok = [r for r in rows if r[2] is not None and not r[5]]
    ng = [r for r in rows if r[5] == '要確認']
    print(f'\n照合 {len([r for r in rows if r[2] is not None])}件 / '
          f'基準を満たす {len(ok)}件 / 要確認 {len(ng)}件 / '
          f'字入り {len([r for r in rows if r[5] and "字入り" in r[5]])}件')
    if ng:
        print('要確認:', ' '.join(r[0] for r in ng))

    if overlay_path and tiles:
        write_overlay(tiles, overlay_path)


def write_overlay(tiles, path):
    """赤=図式のみ / 青=アイコンのみ / 黒=一致 の重ね合わせ画像。"""
    from PIL import ImageDraw, ImageFont
    try:
        font = ImageFont.truetype('/mnt/c/Windows/Fonts/meiryo.ttc', 13)
    except Exception:
        font = ImageFont.load_default()
    cols = 6
    rows_n = math.ceil(len(tiles) / cols)
    cw, ch = 156, 150 + 34
    canvas = Image.new('RGB', (cols * cw + 8, rows_n * ch + 30), 'white')
    dr = ImageDraw.Draw(canvas)
    dr.text((6, 8), '赤=図式のみ / 青=アイコンのみ / 黒=一致（インクのbboxを正規化して重ねた）',
            fill='black', font=font)
    for n, (code, name, truth, icon, aspect, i2t, t2i) in enumerate(tiles):
        ov = np.full((SIZE, SIZE, 3), 255, np.uint8)
        ov[truth & ~icon] = [220, 40, 40]
        ov[icon & ~truth] = [40, 80, 220]
        ov[truth & icon] = [30, 30, 30]
        x, y = (n % cols) * cw + 4, (n // cols) * ch + 28
        dr.text((x, y), f'{code} {name[:8]}', fill='black', font=font)
        dr.text((x, y + 15), f'比率差{aspect:.1f}% 覆{t2i:.0f}/{i2t:.0f}%',
                fill=(110, 110, 110), font=font)
        canvas.paste(Image.fromarray(ov).resize((150, 150), Image.LANCZOS), (x, y + 32))
    canvas.save(path)
    print(f'{path} を書き出しました')


if __name__ == '__main__':
    main()

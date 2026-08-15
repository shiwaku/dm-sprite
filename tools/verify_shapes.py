# -----------------------------------------
# アイコンの形が図式と一致しているかを機械的に判定する。**図式PDFは要らない。**
#
#   python3 tools/verify_shapes.py                    # 全件の数値を出す
#   python3 tools/verify_shapes.py 3504 4119          # 指定コードだけ
#   python3 tools/verify_shapes.py --overlay out.png  # 重ね合わせ画像も出す
#   python3 tools/verify_shapes.py --check            # 基準値と突き合わせ、外れたら終了コード1
#   python3 tools/verify_shapes.py --write-baseline   # 基準値を書き直す
#
# 基準形状は data/zushiki-geometry.json（図式PDFから抜いてリポジトリに置いたもの。
# 作り直すのは tools/dump_zushiki_geometry.py）。判定の基準値は data/shape-baseline.csv。
#
#   図式PDF → [抽出・目視レビュー] → data/zushiki-geometry.json
#                                        ↓ 毎回の自動判定（PDF不要・CIで実行）
#                                    icons/*.svg
#
# **保証できるのは「アイコンが基準形状と一致していること」まで。** 基準形状そのものが
# 図式の正しい読み取りかは、JSON をコミットする時点の目視レビューで担保する。
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
# 判定の目安: 比率差 10%以下、覆い率 いずれも 85%以上。小さな部品を持つ記号
# （41-19 有線柱の架線、42-42 航空灯台の箱）は線幅の差が数値に出やすい。
#
# 比率差は「インクbboxの縦横比を図式側を分母にして比べた相対誤差」なので、
# 絶対の大きさは見ておらず、平たい／細長い記号では数百%に振れる。0%でも形の
# 一致は意味しない。読み方は docs/icon-authoring-guide.md「比率差の読み方」。
# -----------------------------------------
import csv
import filecmp
import io
import json
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

# 記号本体に使われている線幅。大分類ごとに違う（建物等0.6・小物体0.45・
# 土地利用等0.3・波浪観測所だけ0.9）。寸法の引出線は 0.15pt、矢印と数字は塗り（幅0）
# なので、0.3pt 以上の線幅を持つ描画だけを本体とみなす。塗りつぶしの図形は
# 幅を持つ 'fs'（塗り＋線）で描かれているのでこの条件で拾える。
BODY_WIDTHS = (0.3, 0.43, 0.45, 0.6, 0.9)
SIZE = 256          # 正規化後の長辺（px）
TOL = 3             # 膨張の半径（px）。線幅の違いを吸収する
ICON_STROKE = 1.1   # アイコンの線幅(px)。gen_icons.py の W と同じ
# 判定のしきい値。
# 比率差を10%にしているのは、図式が三角形などを「3本の別々の線」で描くのに対し、
# こちらは頂点の欠けを避けるためマイター接合する方針（polyline/poly_band）で、
# 尖った角では意図的にインクが外へ伸びるため。線幅の相対差は truth_raster の
# stroke で揃えているので、残るのはこの接合の違いと丸めの誤差。
# 覆い率のほうが要素の欠け・余分に敏感なので、こちらは85%を維持する
# （41-19 有線柱の架線の誤りは覆い率58.8%で出た）。
ASPECT_NG = 10.0    # 比率差(%)のしきい値
COVER_NG = 85.0     # 覆い率(%)のしきい値

# ○＋文字のコード。字形は書体が違うので覆い率は一致しない（円の比率だけが見どころ）。
GLYPH_CODES = {'2252', '3512', '3513', '3517', '3518', '3527', '3528', '3529', '3531',
               '3539', '3552', '3559', '4224', '4226', '4227', '4245', '7201', '7211'}

# gen_icons.py の trace() で図式の座標をそのまま写した記号。**この判定は自己参照**
# （同じ座標を基準に比べるので必ず一致する）。独立の根拠にはならないので、
# 図式画像と並べた目視レビューの結果を data/shape-baseline.csv の根拠欄に残す。
TRACED = {'6221', '6223', '6316'}

# 図式には描かれているが点アイコンには入れない要素。作図時の判断をここに残す。
EXCLUDE_REASON = {
    '4217': '真形の外枠は記号ではないので除外（点アイコンは極小記号を採る）',
    '4242': '上の箱の外側の縦線2本は2.6mmの寸法を示す補助線なので除外',
    '3508': '下の0.45ptの横線は2500用の変種の上辺（500用は0.6pt）。変種の間隔が'
            '0.62ptしかなく同じ塊として拾われるので除外',
    '3401': '図式欄に真形（門柱の外周＝壁の切れ目と地面の線）と極小の四角が並ぶ。'
            '点アイコンは極小の四角だけを採るので、真形と地面の線を除外',
    '5226': '図式欄に真形（上流部・下流部）と極小が並ぶ。極小は横線1.5mm＋小円2つ。'
            '点アイコンは極小だけを採るので、真形2つを除外',
    '2247': '図式欄に500/1000用（線幅0.6）と2500用（0.45）が横に並ぶ。'
            '500/1000用だけを採る',
    '2255': '図式欄に注記の付け方の例（左）と、寸法が入った記号（右）が横に並ぶ。'
            '寸法が入っている右だけを採る',
    '2256': '2255 と同じ（左は注記の例、右が寸法入りの記号）',
    '2419': '図式欄にトンネルの線の表現（線幅0.45）と極小のアーチ（0.9）が並ぶ。'
            '点アイコンは極小のアーチだけを採る。アーチは「円を描いて下半分を'
            '白い矩形で隠す」描き方なので、矩形と隠れている下半分の弧を除外する',
}

# 数値が基準を外れているが、図式と並べて目視で確認し、理由が説明できるもの。
# 基準値には「確認済」として理由つきで残す（数値は基準値で固定されるので、
# ここに入れても形を黙って変えることはできない）。
REVIEWED = {
    '4253': '図式の実測値をインク外形として扱っているため、図式の描画（中心線＋線幅）'
            'より線幅の半分ぶん小さい。二重円の位置と貫く横線は一致している',
    '4256': '4253 と同じ理由（二重円が線幅の半分ぶん小さい）。貫く斜線は一致している',
}

EXCLUDE = {
    # 真形（実際の外形）の外枠。点アイコンには極小記号だけを採る
    '4217': lambda it: it[0] == 're' and it[2][1][0] - it[2][0][0] > 15,
    # 上の箱の外側にある縦線2本。2.6mm の寸法を示す補助線で、記号ではない
    '4242': lambda it: (it[0] == 'l' and abs(it[2][-1][0] - it[2][0][0]) < 0.1
                        and abs(it[2][-1][1] - it[2][0][1]) > 4.5),
    '3508': lambda it: it[1] < 0.5,
    # 極小の四角（x>313 の re）だけを残す。同じ 1.0mm の四角がもう1つ左にあるが、
    # 真形の門柱・地面の線と同じ塊なのでまとめて落とす
    '3401': lambda it: not (it[0] == 're' and it[2][0][0] > 313),
    # 極小は図式欄の上（y<145）。真形の上流部・下流部はその下にある
    '5226': lambda it: max(p[1] for p in it[2]) >= 145,
    # 2500用（線幅0.45）を落とし、500/1000用（0.6）だけを残す
    '2247': lambda it: it[1] < 0.5,
    # 左に並ぶ注記の例（x<300）を落とし、寸法の入った記号だけを残す
    '2255': lambda it: max(p[0] for p in it[2]) < 300,
    '2256': lambda it: max(p[0] for p in it[2]) < 300,
    # 線の表現（0.45）と、円の下半分（白い矩形で隠されていて見えない）を落とす
    '2419': lambda it: (it[1] < 0.5 or it[0] == 're'
                        or min(p[1] for p in it[2]) >= 188),
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
        # 塗りの色を見る。図式の 'fs'（塗り＋線）はほぼ白塗り＋黒線で、
        # 白塗りは下の線を隠すためのものなので、黒く塗ると別形状になってしまう。
        fill = grp.get('fill')
        filled = bool(fill) and (sum(fill) / len(fill)) < 0.5
        for t in grp['items']:
            pts = [t[1].tl, t[1].br] if t[0] == 're' else [p for p in t[1:] if hasattr(p, 'x')]
            if not pts:
                continue
            if not all(cell['zu'][0] <= p.x <= cell['zu'][1]
                       and cell['y0'] <= p.y <= cell['y1'] for p in pts):
                continue
            got.append((t[0], lw, [(round(p.x, 2), round(p.y, 2)) for p in pts], filled))
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


def truth_raster(items, zoom=12, stroke=None):
    """記号本体だけを引き直したラスタ。

    stroke を与えるとその線幅（pt）で引く。線幅は設計方針で図式と意図的に違うため、
    アイコン側と同じ「図形の大きさに対する線幅の比」に揃えてから比べると、
    形の違いだけを見られる（尖った頂点のマイターの伸び方が揃う）。"""
    xs = [p[0] for it in items for p in it[2]]
    ys = [p[1] for it in items for p in it[2]]
    x0, y0, pad = min(xs), min(ys), 2.0
    doc = fitz.open()
    page = doc.new_page(width=max(xs) - x0 + 2 * pad, height=max(ys) - y0 + 2 * pad)
    shape = page.new_shape()
    for op, lw, pts, *rest in items:
        filled = bool(rest[0]) if rest else False
        lw = stroke if stroke else lw
        p = [(x - x0 + pad, y - y0 + pad) for x, y in pts]
        if op == 'l':
            shape.draw_line(fitz.Point(*p[0]), fitz.Point(*p[-1]))
        elif op == 'c':
            shape.draw_bezier(*[fitz.Point(*q) for q in p[:4]])
        elif op == 're':
            shape.draw_rect(fitz.Rect(p[0][0], p[0][1], p[1][0], p[1][1]))
        # closePath の既定は True。円弧の各セグメントに弦が引かれるので切る
        shape.finish(width=lw, color=(0, 0, 0),
                     fill=(0, 0, 0) if filled else None, closePath=False)
    shape.commit()
    pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    return Image.open(io.BytesIO(pm.tobytes('png'))).convert('L')


ICON_PX = 1024      # アイコンのラスタ化サイズ。64pxキャンバスを何pxで描くか


def svg_raster(path, px=ICON_PX):
    import cairosvg
    png = cairosvg.svg2png(url=path, output_width=px, output_height=px,
                           background_color='white')
    return Image.open(io.BytesIO(png)).convert('L')


def icon_raster(name, px=ICON_PX):
    return svg_raster(os.path.join(ROOT, 'icons', name), px)


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


SAME_ASPECT, SAME_COVER = 2.0, 95.0   # ここを満たせば「同じ形」とみなせる


def icon_names():
    """ファイル名 -> 名称。--similar の表示用。"""
    path = os.path.join(ROOT, 'data', 'icons.csv')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8-sig', newline='') as fp:
        return {r['ファイル名']: r['名称'] for r in csv.DictReader(fp)}


def similar(path, top=10):
    """指定したSVGと形が近い既存アイコンを、近い順に出す。

    拡張DMコードのアイコンを起こす前に「同じ形が既にあるか」を機械的に見るための
    もの。図式との照合と同じ土俵（インクbboxで正規化し、線幅の差は膨張で吸収）で
    比べるので、大きさの違いは無視され、形だけが効く。"""
    target = os.path.abspath(path)
    a, asz = normalize(svg_raster(target))
    if a is None:
        sys.exit(f'{path} にインクがありません')
    names = icon_names()
    rows = []
    for fname in sorted(os.listdir(os.path.join(ROOT, 'icons'))):
        if not fname.endswith('.svg'):
            continue
        full = os.path.join(ROOT, 'icons', fname)
        if os.path.abspath(full) == target:
            continue
        b, bsz = normalize(icon_raster(fname))
        if b is None:
            continue
        aspect = abs(asz[0] / asz[1] - bsz[0] / bsz[1]) / (asz[0] / asz[1]) * 100
        rows.append((fname, aspect, coverage(a, b), coverage(b, a),
                     filecmp.cmp(target, full, shallow=False)))
    rows.sort(key=lambda r: (-min(r[2], r[3]), r[1]))

    print(f'{os.path.basename(path)} と形が近い既存アイコン\n')
    print(f'{"ファイル":26}{"比率差":>8}{"→既存":>8}{"既存→":>8}  判定  名称')
    for fname, aspect, i2j, j2i, same in rows[:top]:
        if same:
            mark = '同一'
        elif aspect <= SAME_ASPECT and min(i2j, j2i) >= SAME_COVER:
            mark = '同形'
        elif aspect <= ASPECT_NG and min(i2j, j2i) >= COVER_NG:
            mark = '近い'
        else:
            mark = '—  '
        print(f'{fname:26}{aspect:7.1f}%{i2j:7.1f}%{j2i:7.1f}%  {mark}  '
              f'{names.get(fname, "")}')
    print(f'\n「同形」以上が出たら、そのアイコンで代替できないか検討する。'
          f'\n代替する場合、スプライトには足さない。利用側がそのキーを指し、'
          f'\n対応と根拠は利用側のプロジェクトに記録する。')


GEOMETRY = os.path.join(ROOT, 'data', 'zushiki-geometry.json')
BASELINE = os.path.join(ROOT, 'data', 'shape-baseline.csv')
# 基準値からのずれの許容。作図を変えれば必ずこれを超えるので、基準値の差分が
# レビューに出る（=形を黙って変えられない）。
TOL_ASPECT, TOL_COVER = 0.5, 1.0


def load_geometry():
    if not os.path.exists(GEOMETRY):
        sys.exit(f'{GEOMETRY} がありません。\n'
                 f'  python3 tools/dump_zushiki_geometry.py <図式PDF> で作ってください')
    with open(GEOMETRY, encoding='utf-8') as fp:
        return json.load(fp)


def override_codes():
    """図式のデータタイプ以外（実データなど）を根拠にアイコン対象にしたコード。

    図式に点記号の定義が無いので、図式との形の照合はできない（意匠の根拠が図面側）。"""
    path = os.path.join(ROOT, 'data', 'symbols-overrides.csv')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8-sig', newline='') as fp:
        return {r['コード']: r.get('理由', '') for r in csv.DictReader(fp)}


def verdict(code, items, aspect, i2t, t2i):
    """判定の区分と、数値で見るべきかを返す。"""
    ov = override_codes()
    if code in ov and '実データ' in ov[code] or code in ov and '図式のデータタイプは' in ov[code]:
        return '図式外', '図式に点記号の定義が無く、意匠の根拠は図面の実測'
    if not items:
        return '検証不可', '図式が塗りだけで描かれていて基準形状が取れない'
    if code in TRACED:
        return '座標写し', '図式の座標を写したので自己参照。目視レビュー済み'
    if code in GLYPH_CODES:
        return '字入り', '字形は書体差（図式の書体ではなく Noto Sans JP）'
    if code in EXCLUDE:
        return '判断あり', EXCLUDE_REASON.get(code, '図式の一部を除外')
    if aspect is None:
        return '測定不可', ''
    if aspect <= ASPECT_NG and min(i2t, t2i) >= COVER_NG:
        return '一致', ''
    if code in REVIEWED:
        return '確認済', REVIEWED[code]
    return '要確認', ''


def measure(code, fname, geom):
    entry = geom.get(code)
    if entry is None:
        return None
    items = [(it['op'], it['w'], [tuple(p) for p in it['pts']], it.get('fill', False))
             for it in entry['items']]
    if not items:
        return dict(code=code, name=entry['name'], items=[], aspect=None,
                    i2t=None, t2i=None, truth=None, icon=None)
    icon, isz = normalize(icon_raster(fname))
    # 図式の線幅をアイコン側と同じ相対太さに揃える（形だけを比べるため）
    xs = [p[0] for it in items for p in it[2]]
    ys = [p[1] for it in items for p in it[2]]
    span_pt = max(max(xs) - min(xs), max(ys) - min(ys))
    stroke = None
    if icon is not None and isz:
        # isz は ICON_PX 基準の画素数なので、64pxキャンバス上の大きさに直す
        icon_span = max(isz) * 64 / ICON_PX
        stroke = ICON_STROKE / icon_span * span_pt
    truth, tsz = normalize(truth_raster(items, stroke=stroke))
    if truth is None or icon is None:
        return dict(code=code, name=entry['name'], items=items, aspect=None,
                    i2t=None, t2i=None, truth=None, icon=None)
    ta, ia = tsz[0] / tsz[1], isz[0] / isz[1]
    return dict(code=code, name=entry['name'], items=items,
                aspect=abs(ta - ia) / ta * 100,
                i2t=coverage(icon, truth), t2i=coverage(truth, icon),
                truth=truth, icon=icon)


def load_baseline():
    if not os.path.exists(BASELINE):
        return {}
    with open(BASELINE, encoding='utf-8-sig', newline='') as fp:
        return {r['コード']: r for r in csv.DictReader(fp)}


def write_baseline(rows):
    cols = ['コード', '名称', '判定', '比率差', 'アイコン→図式', '図式→アイコン', '根拠']
    with open(BASELINE, 'w', encoding='utf-8', newline='') as fp:
        w = csv.writer(fp, lineterminator='\n')
        w.writerow(cols)
        for r in rows:
            v, why = r['verdict']
            num = (lambda x: '' if x is None else f'{x:.1f}')
            w.writerow([r['code'], r['name'], v, num(r['aspect']),
                        num(r['i2t']), num(r['t2i']), why])
    print(f'{BASELINE} を書き出しました（{len(rows)}件）')


def main():
    args = sys.argv[1:]
    if '--similar' in args:
        i = args.index('--similar')
        similar(args[i + 1])
        return
    overlay_path = None
    if '--overlay' in args:
        i = args.index('--overlay')
        overlay_path = args[i + 1]
        del args[i:i + 2]
    do_check = '--check' in args
    do_write = '--write-baseline' in args
    only = {a for a in args if not a.startswith('--')}

    geom = load_geometry()
    rows, tiles = [], []
    for code, fname in targets(only):
        m = measure(code, fname, geom)
        if m is None:
            rows.append(dict(code=code, name='', aspect=None, i2t=None, t2i=None,
                             verdict=('基準なし', 'data/zushiki-geometry.json に無い')))
            continue
        m['verdict'] = verdict(code, m['items'], m['aspect'], m['i2t'], m['t2i'])
        rows.append(m)
        if m['truth'] is not None:
            tiles.append((code, m['name'], m['truth'], m['icon'],
                          m['aspect'], m['i2t'], m['t2i']))

    print(f'{"コード":6}{"名称":18}{"比率差":>8}{"ア→図":>8}{"図→ア":>8}  判定')
    for r in rows:
        num = (lambda x: f'{x:7.1f}%' if x is not None else f'{"—":>8}')
        print(f'{r["code"]:6}{r["name"][:16]:18}{num(r["aspect"])}{num(r["i2t"])}'
              f'{num(r["t2i"])}  {r["verdict"][0]}'
              + (f' — {r["verdict"][1]}' if r['verdict'][1] else ''))

    from collections import Counter
    tally = Counter(r['verdict'][0] for r in rows)
    print('\n' + ' / '.join(f'{k} {v}件' for k, v in sorted(tally.items())))

    if do_write:
        write_baseline(rows)
    if overlay_path and tiles:
        write_overlay(tiles, overlay_path)

    if do_check:
        base = load_baseline()
        if not base:
            sys.exit(f'{BASELINE} がありません。--write-baseline で作ってください')
        bad = []
        for r in rows:
            b = base.get(r['code'])
            if b is None:
                bad.append(f'{r["code"]} は基準値に無い（--write-baseline で記録する）')
                continue
            if b['判定'] != r['verdict'][0]:
                bad.append(f'{r["code"]} 判定が変わった: {b["判定"]} → {r["verdict"][0]}')
            for key, col, tol in (('aspect', '比率差', TOL_ASPECT),
                                  ('i2t', 'アイコン→図式', TOL_COVER),
                                  ('t2i', '図式→アイコン', TOL_COVER)):
                want, got = b[col].strip(), r[key]
                if not want and got is None:
                    continue
                if not want or got is None:
                    bad.append(f'{r["code"]} {col} の有無が変わった')
                    continue
                if abs(float(want) - got) > tol:
                    bad.append(f'{r["code"]} {col} が {want}% → {got:.1f}% に変わった')
        extra = sorted(set(base) - {r['code'] for r in rows})
        for code in extra:
            bad.append(f'{code} は基準値にあるがアイコンが無い')
        if bad:
            print('\n基準値と合いません:')
            for b in bad:
                print('  -', b)
            print('\n形を変えたのであれば --write-baseline で基準値を更新し、'
                  '差分をレビューに出してください。')
            sys.exit(1)
        print('\n基準値と一致しました。')


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

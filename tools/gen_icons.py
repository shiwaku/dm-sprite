# -----------------------------------------
# 公共測量標準図式の記号を SVG 化するための作図ヘルパと、その適用例。
#
#   python3 tools/gen_icons.py            # tools/out_icons/ に書き出す
#   python3 tools/gen_icons.py --install  # icons/ に直接書き出す
#
# 設計基準は docs/svg-design-spec.md に従う。
#   64x64 / viewBox="0 0 64 64" / ルート fill="none" / 単色 fill="black" / 1パス
#   ストロークは使わず、線はすべて塗りパス（アウトライン）で表現する。
#
# 形状と寸法は「作業規程の準則 付録7 公共測量標準図式」の図式欄から読み取る。
# 大きさは mm 比の厳密再現ではなく、既存アイコンの実測レンジ
#   （bbox 10〜22px・線幅 約1.1px・中心 (32,32)）に合わせる方針。
# 読み取り手順と検証手順は docs/icon-authoring-guide.md を参照。
#
# 末尾は追加済みコードの作図例（2026-08 の標準図式6件、道路台帳向け8件）。
# 新しい記号を足すときは同じ書き方で write(...) を1行ずつ増やす。
# -----------------------------------------
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = (os.path.join(ROOT, 'icons') if '--install' in sys.argv
       else os.path.join(ROOT, 'tools', 'out_icons'))
os.makedirs(OUT, exist_ok=True)

W = 1.1          # 線幅（px）。既存アイコンの実測中央値
CX = CY = 32.0   # キャンバス中心

def f(v):
    """座標を2桁に丸めて出力（既存アイコンと同じ精度）。"""
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return s if s not in ('-0', '') else '0'


def poly(pts, close=True):
    d = 'M' + ' '.join(f'{f(x)} {f(y)}' for x, y in pts[:1])
    for x, y in pts[1:]:
        d += f'L{f(x)} {f(y)}'
    return d + ('Z' if close else '')


def seg(p0, p1, w=W):
    """始点p0→終点p1の線分を、太さwの矩形（バットキャップ）として塗りパス化。"""
    (x0, y0), (x1, y1) = p0, p1
    dx, dy = x1 - x0, y1 - y0
    L = math.hypot(dx, dy)
    nx, ny = -dy / L * w / 2, dx / L * w / 2
    return poly([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny),
                 (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])


def polyline(pts, w=W):
    """折れ線をマイター接合で太さwの塗りパスにする。頂点に欠けが出ないようにする。"""
    def off(p0, p1, s):
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy)
        return (-dy / L * w / 2 * s, dx / L * w / 2 * s)

    def side(sign):
        out = []
        for i in range(len(pts) - 1):
            n = off(pts[i], pts[i + 1], sign)
            a = (pts[i][0] + n[0], pts[i][1] + n[1])
            b = (pts[i + 1][0] + n[0], pts[i + 1][1] + n[1])
            if not out:
                out.append(a)
            else:
                # 直前の辺との交点（マイター点）に置き換える
                p, q = out[-2], out[-1]
                d1 = (q[0] - p[0], q[1] - p[1])
                d2 = (b[0] - a[0], b[1] - a[1])
                den = d1[0] * d2[1] - d1[1] * d2[0]
                if abs(den) > 1e-9:
                    t = ((a[0] - p[0]) * d2[1] - (a[1] - p[1]) * d2[0]) / den
                    out[-1] = (p[0] + d1[0] * t, p[1] + d1[1] * t)
                else:
                    out.append(a)
            out.append(b)
        return out

    return poly(side(1) + list(reversed(side(-1))))


def _arc_bez(cx, cy, r, a0, a1):
    """角度a0→a1（ラジアン）の円弧を3次ベジエ列で近似。90度ごとに分割。"""
    out = []
    n = max(1, math.ceil(abs(a1 - a0) / (math.pi / 2)))
    step = (a1 - a0) / n
    k = 4 / 3 * math.tan(step / 4)
    for i in range(n):
        s = a0 + step * i
        e = s + step
        x0, y0 = cx + r * math.cos(s), cy + r * math.sin(s)
        x1, y1 = cx + r * math.cos(e), cy + r * math.sin(e)
        c1 = (x0 - k * r * math.sin(s), y0 + k * r * math.cos(s))
        c2 = (x1 + k * r * math.sin(e), y1 - k * r * math.cos(e))
        out.append(((x0, y0), c1, c2, (x1, y1)))
    return out


def _bez_d(segs, start=True):
    d = ''
    if start:
        d += f'M{f(segs[0][0][0])} {f(segs[0][0][1])}'
    for _, c1, c2, p in segs:
        d += f'C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p[0])} {f(p[1])}'
    return d


def arc_band(cx, cy, r, a0, a1, w=W):
    """中心(cx,cy)・半径r・a0→a1 の円弧を、太さwの円環帯として塗りパス化。"""
    outer = _arc_bez(cx, cy, r + w / 2, a0, a1)
    inner = _arc_bez(cx, cy, r - w / 2, a1, a0)
    d = _bez_d(outer)
    d += f'L{f(inner[0][0][0])} {f(inner[0][0][1])}'
    d += _bez_d(inner, start=False)
    return d + 'Z'


def ring(cx, cy, r, w=W):
    """外円（時計回り）＋内円（反時計回り）で穴あきリングを作る。"""
    outer = _bez_d(_arc_bez(cx, cy, r + w / 2, 0, 2 * math.pi)) + 'Z'
    inner = _bez_d(_arc_bez(cx, cy, r - w / 2, 2 * math.pi, 0)) + 'Z'
    return outer + inner


def dot(cx, cy, r):
    """半径rの塗りつぶし円。"""
    return _bez_d(_arc_bez(cx, cy, r, 0, 2 * math.pi)) + 'Z'


def ellipse_band(cx, cy, rx, ry, w=W):
    """楕円の輪郭を太さwの帯にする。半径を内外に w/2 ずらす近似で、細い帯なら十分。"""
    def ell(rx_, ry_, a0, a1):
        return [tuple((cx + x * rx_, cy + y * ry_) for x, y in seg)
                for seg in _arc_bez(0, 0, 1, a0, a1)]

    outer = _bez_d(ell(rx + w / 2, ry + w / 2, 0, 2 * math.pi)) + 'Z'
    inner = _bez_d(ell(rx - w / 2, ry - w / 2, 2 * math.pi, 0)) + 'Z'
    return outer + inner


def poly_band(pts, w=W):
    """閉じた多角形の輪郭を太さwの帯にする。pts は輪郭の中心線（頂点は反復しない）。

    polyline() で始点に戻ると始点だけ接合されずバットキャップが残り、その分だけ
    形が非対称になる（三角形で中心が 0.3px ずれた）。全頂点をマイターで通すため、
    外側・内側の多角形を作って ring() と同じく逆回りで抜く。"""
    n = len(pts)

    def offset(s):
        out = []
        for i in range(n):
            p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
            n1 = _unit_normal(p0, p1)
            n2 = _unit_normal(p1, p2)
            k = 1 + n1[0] * n2[0] + n1[1] * n2[1]      # マイター長の係数
            if abs(k) < 1e-9:
                mx, my = n1
            else:
                mx, my = (n1[0] + n2[0]) / k, (n1[1] + n2[1]) / k
            out.append((p1[0] + mx * w / 2 * s, p1[1] + my * w / 2 * s))
        return out

    return poly(offset(1)) + poly(list(reversed(offset(-1))))


def _unit_normal(p0, p1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    return (-dy / L, dx / L)


def rect_band(x0, y0, x1, y1, w=W):
    """矩形の輪郭を太さwの帯にする。x0..x1,y0..y1 は輪郭の中心線。"""
    h = w / 2
    return (poly([(x0 - h, y0 - h), (x1 + h, y0 - h),
                  (x1 + h, y1 + h), (x0 - h, y1 + h)]) +
            poly([(x0 + h, y0 + h), (x0 + h, y1 - h),
                  (x1 - h, y1 - h), (x1 - h, y0 + h)]))


def round_rect_band(x0, y0, x1, y1, r, w=W):
    """角丸矩形の輪郭を太さwの帯にする。角の円弧4本＋直線4本を突き合わせる。"""
    q = math.pi / 2
    d = ''
    for cx, cy, a0 in ((x1 - r, y0 + r, -q), (x1 - r, y1 - r, 0),
                       (x0 + r, y1 - r, q), (x0 + r, y0 + r, 2 * q)):
        d += arc_band(cx, cy, r, a0, a0 + q, w)
    return (d + seg((x0 + r, y0), (x1 - r, y0), w) +
            seg((x0 + r, y1), (x1 - r, y1), w) +
            seg((x0, y0 + r), (x0, y1 - r), w) +
            seg((x1, y0 + r), (x1, y1 - r), w))


# 字入り記号（○＋漢字など）に使う書体。SIL OFL なので MIT の本リポジトリに取り込める。
FONT_CANDIDATES = [
    '/mnt/c/Windows/Fonts/NotoSansJP-VF.ttf',
    'C:/Windows/Fonts/NotoSansJP-VF.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansJP[wght].ttf',
    os.path.expanduser('~/.fonts/NotoSansJP-VF.ttf'),
]


def _font(weight):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError(
            'Noto Sans JP が見つかりません。FONT_CANDIDATES にパスを追加してください。')
    return instancer.instantiateVariableFont(TTFont(path), {'wght': weight})


def glyph(ch, height, cx, cy, weight=400):
    """Noto Sans JP（OFL）から1文字のアウトラインを取り出し、指定サイズ・中心に配置。"""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.transformPen import TransformPen

    font = _font(weight)
    gs = font.getGlyphSet()
    gname = font.getBestCmap()[ord(ch)]
    bp = BoundsPen(gs)
    gs[gname].draw(bp)
    x0, y0, x1, y1 = bp.bounds
    sc = height / (y1 - y0)
    # フォント座標はY上向き。(sc,-sc) で反転し、字面bboxの中心を(cx,cy)に合わせる。
    # transform属性は使わず、パス座標に焼き込んで1パスにまとめる（既存アイコンの慣例）。
    tx = cx - (x0 + x1) / 2 * sc
    ty = cy + (y0 + y1) / 2 * sc
    pen = SVGPathPen(gs)
    gs[gname].draw(TransformPen(pen, (sc, 0, 0, -sc, tx, ty)))
    return pen.getCommands()


def glyph_box(ch, size, cx, cy, weight=400):
    """字面bboxの長辺を size に合わせて1文字を配置する。

    glyph() は高さで揃えるので、「工」のような横長の字だと幅が出すぎて円から
    はみ出す。縦長・正方形に近い字では glyph(height=size) と同じ結果になる。"""
    from fontTools.pens.boundsPen import BoundsPen

    font = _font(weight)
    gs = font.getGlyphSet()
    bp = BoundsPen(gs)
    gs[font.getBestCmap()[ord(ch)]].draw(bp)
    x0, y0, x1, y1 = bp.bounds
    h = size if (y1 - y0) >= (x1 - x0) else size * (y1 - y0) / (x1 - x0)
    return glyph(ch, h, cx, cy, weight)


def text(s, height, cx, cy, weight=400, width=None):
    """複数文字を字送りどおりに並べ、字面bboxの中心を(cx,cy)に合わせて1パスにする。
    width を与えると横方向だけ拡縮して図式の縦横比に合わせる。"""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.transformPen import TransformPen

    font = _font(weight)
    gs = font.getGlyphSet()
    cmap = font.getBestCmap()
    names = [cmap[ord(ch)] for ch in s]
    bp = BoundsPen(gs)
    adv = 0.0
    for g in names:                       # 字送りを積みながら全体の字面bboxを測る
        gs[g].draw(TransformPen(bp, (1, 0, 0, 1, adv, 0)))
        adv += gs[g].width
    x0, y0, x1, y1 = bp.bounds
    sy = height / (y1 - y0)
    sx = width / (x1 - x0) if width else sy
    tx = cx - (x0 + x1) / 2 * sx
    ty = cy + (y0 + y1) / 2 * sy
    pen = SVGPathPen(gs)
    adv = 0.0
    for g in names:
        gs[g].draw(TransformPen(pen, (sx, 0, 0, -sy, tx + adv * sx, ty)))
        adv += gs[g].width
    return pen.getCommands()


def trace(items, ink, samples=10):
    """図式の実測座標をそのままパスに写す。曲線が主体で手で組みにくい記号に使う。

    items は [(op, [(x,y), ...]), ...]。op は 'l'（線分）'c'（3次ベジエ）'re'（矩形）で、
    座標は図式PDFの pt。ink はインク外形の目標(px)で、長辺がこれに収まる倍率にする。

    **この関数を使った記号は、図式の座標をそのまま写しているため
    verify_shapes.py の照合が自己参照になる**（同じ座標を基準に比べるので必ず一致する）。
    真形と極小記号のどちらを採るか、どの要素を落とすかの判断は照合では出てこないので、
    使うときは図式の画像と並べた目視確認を必ず行う。

    端点がつながっている要素はひとつの折れ線としてつなぐ（接合が効いて欠けが出ない）。"""
    pts_all = [p for _, pts in items for p in pts]
    x0 = min(p[0] for p in pts_all)
    x1 = max(p[0] for p in pts_all)
    y0 = min(p[1] for p in pts_all)
    y1 = max(p[1] for p in pts_all)
    k = (ink - W) / max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def to_px(p):
        return ((p[0] - cx) * k + CX, (p[1] - cy) * k + CY)

    def bez(p, t):
        """3次ベジエ上の点。"""
        u = 1 - t
        return (u ** 3 * p[0][0] + 3 * u * u * t * p[1][0] + 3 * u * t * t * p[2][0]
                + t ** 3 * p[3][0],
                u ** 3 * p[0][1] + 3 * u * u * t * p[1][1] + 3 * u * t * t * p[2][1]
                + t ** 3 * p[3][1])

    d = ''
    chain = []
    for op, pts in list(items) + [(None, None)]:
        if op == 're':
            (rx0, ry0), (rx1, ry1) = to_px(pts[0]), to_px(pts[1])
            d += rect_band(rx0 + W / 2, ry0 + W / 2, rx1 - W / 2, ry1 - W / 2)
            continue
        if op == 'l':
            seq = [to_px(pts[0]), to_px(pts[-1])]
        elif op == 'c':
            seq = [to_px(bez(pts, i / samples)) for i in range(samples + 1)]
        else:
            seq = None
        # 直前の折れ線と端点が一致していればつなぐ
        if seq and chain and abs(chain[-1][0] - seq[0][0]) < 0.05 \
                and abs(chain[-1][1] - seq[0][1]) < 0.05:
            chain += seq[1:]
            continue
        if len(chain) >= 2:
            d += polyline(chain)
        chain = seq or []
    return d


def ink_bbox(d):
    """パスデータのインク外形 (x0, y0, x1, y1)。

    ここのヘルパはどれも輪郭そのものを塗りパスとして出すので、座標の範囲が
    そのままインクの範囲になる（ストローク幅を足す必要がない）。"""
    v = [float(s) for s in re.findall(r'-?\d+(?:\.\d+)?', d)]
    xs, ys = v[0::2], v[1::2]
    return min(xs), min(ys), max(xs), max(ys)


def center_ink(d, cx=None, cy=None):
    """インク外形の中心を (cx, cy) に合わせて平行移動する。

    マイター接合は尖った頂点で外へ伸び、バットキャップは伸びないので、
    寸法どおりに組んだだけでは中心が 0.5px ほどずれることがある。"""
    cx = CX if cx is None else cx
    cy = CY if cy is None else cy
    x0, y0, x1, y1 = ink_bbox(d)
    dx, dy = cx - (x0 + x1) / 2, cy - (y0 + y1) / 2
    it = iter(range(10 ** 9))
    return re.sub(r'-?\d+(?:\.\d+)?',
                  lambda m: f(float(m.group(0)) + (dx if next(it) % 2 == 0 else dy)), d)


def write(code, body, note):
    svg = (f'<svg width="64" height="64" viewBox="0 0 64 64" fill="none" '
           f'xmlns="http://www.w3.org/2000/svg">\n'
           f'<path d="{body}" fill="black"/>\n</svg>\n')
    path = os.path.join(OUT, f'dm-{code}.svg')
    with open(path, 'w', encoding='utf-8') as fp:
        fp.write(svg)
    print(f'dm-{code}.svg  {note}')


# ---- 35-19 役場支所及び出張所 ----------------------------------------
# 図式: 単純な円。直径 4.0mm(500/1000) / 2.5mm(2500)。
# 既存の官公署系（3525/3526/3536）が外径22pxで揃っているため、それに合わせる。
write('3519', ring(CX, CY, 11 - W / 2), '円 外径22px（3525/3526/3536と同径）')

# ---- 35-31 保健所 ----------------------------------------------------
# 図式: 円の中に「保」。直径 4.0mm / 2.5mm。円は3519と同径。
# 図式を実測すると字は円にほぼ内接しており、字高/円外径 = 0.735、字幅/円外径 = 0.785。
# 外径22px に対して字高 16.2px（= 22 * 0.735）を採る。
write('3531', ring(CX, CY, 11 - W / 2) + glyph('保', 16.2, CX, CY, weight=400),
      '円22px＋「保」高さ16.2px（Noto Sans JP 400 / OFL）')

# ---- 63-35 はい松地 --------------------------------------------------
# 図式: 下向きの矢印。2.0×1.5mm(500-2500) / 1.5×1.2mm(5000)。
# 軸は全高、矢羽根は図式実測で上端から 0.364 の位置から始まる（＝下側 0.636 が矢羽根）。
# 植生系の既存（6334 荒地 13.5×12.5）に合わせ、幅14px・高さ10.5px（=2.0:1.5）とする。
w6335, h6335 = 14.0, 10.5
bx = w6335 / 2                 # 矢羽根の横の張り出し
by = h6335 * (1 - 0.364)       # 矢羽根の縦の長さ
# 矢羽根の先端はマイター接合のぶんだけ合流点より下に出る。その差を見込んで
# 全体を上にずらし、インクの外形が (32,32) を中心にするようにする。
ext = (W / 2) * math.hypot(bx, by) / bx
top = CY - (h6335 + ext) / 2
bot = top + h6335
d = (polyline([(CX - bx, bot - by), (CX, bot), (CX + bx, bot - by)]) +
     seg((CX, top), (CX, bot)))
write('6335', d, '下向き矢印 14×10.5px（矢羽根は上端から0.364）')

# ---- 22-19 道路のトンネル --------------------------------------------
# 図式: 極小は「1/3円」のアーチ（∩）、幅1.5mm。
# 弦=14px とすると中心角120度・半径 7/sin60 = 8.08px、矢高 4.04px。
chord = 14.0
r2219 = (chord / 2) / math.sin(math.radians(60))
sag = r2219 * (1 - math.cos(math.radians(60)))
cy2219 = CY - sag / 2 + r2219          # 円中心（アーチは上に凸）
d = arc_band(CX, cy2219, r2219, math.radians(210), math.radians(330))
write('2219', d, f'1/3円アーチ 弦14px・矢高{sag:.2f}px')

# ---- 52-27 せき ------------------------------------------------------
# 図式: 極小は長さ3.0mm・間隔0.5mm の2本線。上が破線（1.0mm線・1.0mm間隔）、下が実線。
# 3.0mm=18px とすると 0.5mm=3px、1.0mm=6px。
L, gap = 18.0, 3.0
x0 = CX - L / 2
yu, yl = CY - gap / 2, CY + gap / 2
d = (seg((x0, yu), (x0 + 6, yu)) +          # 上段 破線1本目
     seg((x0 + 12, yu), (x0 + 18, yu)) +    # 上段 破線2本目
     seg((x0, yl), (x0 + L, yl)))           # 下段 実線
write('5227', d, '上=破線(6-6-6)・下=実線 長さ18px・間隔3px')

# ---- 72-12 露岩 ------------------------------------------------------
# 図式: 上に開いた半円（幅1.5mm・深さ0.75mm）＋弦の中央に短い線分（0.5mm）。
# 幅14px とすると半径7px、線分長 14*(0.5/1.5)=4.67px。
w7212 = 14.0
r7212 = w7212 / 2
chord_y = CY - r7212 / 2
bar = w7212 * (0.5 / 1.5)
d = (arc_band(CX, chord_y, r7212, 0, math.pi) +
     seg((CX - bar / 2, chord_y), (CX + bar / 2, chord_y)))
write('7212', d, f'半円(幅14・深さ7px)＋弦中央の線分{bar:.2f}px')


# =====================================================================
# 2026-08 追加分。道路台帳平面図（地図情報レベル500）で使われるが
# スプライトに無かったコードのうち、標準図式に記号定義があるもの8件。
# ページ番号は「作業規程の準則 付録7 公共測量標準図式」（2025-03-06版）のもの。
# 小物体系の実寸スケールは、既存のマンホール（極小φ2.0mm→18.56px）から
# 約9.3px/mm と読める。以下はこれを目安にしつつ、10〜22pxのレンジに収める。
# =====================================================================

# ---- 22-21 バス停（点E5） --------------------------------------------
# 図式(p.51): 円φ1.0の下に柱、全高2.0、下端に横棒1.0。
# 全高 18.5px（=2.0mm × 9.25px/mm）とする。
s = 9.25
h2221, dia2221, bar2221 = 2.0 * s, 1.0 * s, 1.0 * s
cy2221 = CY - h2221 / 2 + dia2221 / 2       # 円の中心
ybar = CY + h2221 / 2 - W / 2               # 横棒の中心線
d = (ring(CX, cy2221, (dia2221 - W) / 2) +
     seg((CX, cy2221 + dia2221 / 2), (CX, ybar)) +
     seg((CX - bar2221 / 2, ybar), (CX + bar2221 / 2, ybar)))
write('2221', d, f'円φ{dia2221:.2f}＋柱・全高{h2221:.1f}px')

# ---- 22-46 信号灯（方向E6） ------------------------------------------
# 図式(p.53): 挿入点の小円φ0.5 ―連結線0.8― 角丸箱2.0×1.0（中に灯φ0.3を3つ）。
# 方向レイヤなので水平右向きに作図する（図式もその向き）。
# 全長3.3mmを26px（7.9px/mm）とする。角丸半径は図式実測で箱の高さの1/3。
s = 7.9
d0, lnk = 0.5 * s, 0.8 * s
bw, bh = 2.0 * s, 1.0 * s
xl = CX - (d0 + lnk + bw) / 2               # インクの左端
bx0 = xl + d0 + lnk                         # 箱の左端（外形）
d = (ring(xl + d0 / 2, CY, (d0 - W) / 2) +
     seg((xl + d0, CY), (bx0, CY)) +
     round_rect_band(bx0 + W / 2, CY - bh / 2 + W / 2,
                     bx0 + bw - W / 2, CY + bh / 2 - W / 2, bh / 3 - W / 2))
for i in (1, 2, 3):
    d += dot(bx0 + bw * i / 4, CY, 0.3 * s / 2)
write('2246', d, f'小円φ{d0:.2f}＋連結線＋角丸箱{bw:.1f}×{bh:.1f}px・灯3つ（右向き）')

# ---- 22-61 電話ボックス（点E5） --------------------------------------
# 図式(p.54): 円φ2.5の中に受話器。円の外径を22pxとする。
# 受話器は図式を実測した比率で組む（弧の半径=外径の0.39、受話部の小円=外径の0.20、
# 小円の中心は円心から (-0.19,-0.19) と (-0.13,+0.25)）。
D = 22.0
ra = 0.382 * D                              # 受話器の弧の半径
p_up = (CX - 0.186 * D, CY - 0.185 * D)     # 受話部（上）
p_lo = (CX - 0.128 * D, CY + 0.250 * D)     # 受話部（下）
a0, a1 = math.radians(200), math.radians(470)   # 左側を開けて時計回りに270°
d = (ring(CX, CY, (D - W) / 2) +
     arc_band(CX, CY, ra, a0, a1) +
     seg((CX + ra * math.cos(a0), CY + ra * math.sin(a0)), p_up) +
     seg((CX + ra * math.cos(a1), CY + ra * math.sin(a1)), p_lo) +
     ring(p_up[0], p_up[1], (0.20 * D - W) / 2) +
     ring(p_lo[0], p_lo[1], (0.20 * D - W) / 2))
write('2261', d, f'円 外径{D:.0f}px＋受話器（弧φ{ra * 2:.2f}・受話部φ{0.2 * D:.2f}）')

# ---- 22-62 郵便ポスト（点E5） ----------------------------------------
# 図式(p.54): 円φ2.5の中に投函口の横長矩形。2261と同径にする。
# 投函口は図式実測で 幅=外径の0.57・高さ=0.20、中心は円心から上に外径の0.25。
D = 22.0
sw, sh = 0.57 * D, 0.20 * D
sy = CY - 0.25 * D
d = (ring(CX, CY, (D - W) / 2) +
     rect_band(CX - sw / 2 + W / 2, sy - sh / 2 + W / 2,
               CX + sw / 2 - W / 2, sy + sh / 2 - W / 2))
write('2262', d, f'円 外径{D:.0f}px＋投函口{sw:.2f}×{sh:.2f}px')

# ---- 35-59 公衆便所（点E5） ------------------------------------------
# 図式(p.75): 文字「W.C」4.0×2.0mm（2500は3.0×1.5mm）。
# 文字系の既存（7201「(土)」26×15、7211「(岩)」25×15）に合わせ 22×11px とする。
# 素の字幅は縦横比 約2.8:1 なので、図式の 2:1 に合わせて横だけ詰める。
# 詰めるぶん縦画が細るので、ウェイトは500（既存の線幅約1.1pxに合わせる）。
d = text('W.C', 11.0, CX, CY, weight=500, width=22.0)
write('3559', d, '「W.C」22×11px（Noto Sans JP 500 / OFL）')

# ---- 41-32 電話柱（点E5＋方向E6） ------------------------------------
# 図式(p.76): 円φ1.0の中に水平線＋架線2本。図式の点線は寸法の引き出し線なので
# 記号には含めず、実線だけを採る。架線の角度は図式実測で 210.1°/344.3°
# （画面座標・Y下向き・右が0°）、長さは円の縁から直径1.0ぶん。
# 隣の41-19 有線柱は「円＋垂直線」、41-42 電力柱は「円のみ」で区別される。
# 取得位置は柱の中心なので、円の中心をキャンバス中心 (32,32) に置く。
# 大きさは小物体系の実寸スケール 9.3px/mm（マンホール極小φ2.0mm→18.56px）による。
s = 9.3
D4132 = 1.0 * s                              # 円の外径
ARM = 1.0 * s                                # 架線の長さ（円の縁から）


def haisen(dia, length, deg):
    """円の縁から外へ伸びる架線1本。degは画面座標（Y下向き・右が0°）。"""
    a = math.radians(deg)
    return seg((CX + dia / 2 * math.cos(a), CY + dia / 2 * math.sin(a)),
               (CX + (dia / 2 + length) * math.cos(a), CY + (dia / 2 + length) * math.sin(a)))


d = (ring(CX, CY, (D4132 - W) / 2) +
     seg((CX - (D4132 / 2 - W), CY), (CX + (D4132 / 2 - W), CY)) +
     haisen(D4132, ARM, 210.1) + haisen(D4132, ARM, 344.3))
write('4132', d, f'円 外径{D4132:.1f}px＋水平線＋架線2本(210.1°/344.3°)')

# ---- 41-42 電力柱（点E5＋方向E6） ------------------------------------
# 図式(p.77): 円φ1.0＋架線3本。実測で 30.3°/173.3°/323.9°、長さは4132と同じ。
d = ring(CX, CY, (D4132 - W) / 2)
for a in (30.3, 173.3, 323.9):
    d += haisen(D4132, ARM, a)
write('4142', d, f'円 外径{D4132:.1f}px＋架線3本(30.3°/173.3°/323.9°)')

# ---- 73-06 公共基準点（多角点等）（点E5） ----------------------------
# 図式(p.123): 三重の同心円。外径2.5mm・中1.5mm・内0.7mm（実測）、線0.3mm。
# 既存の73-04 公共基準点（三角点）18.69pxに合わせ、外径18.5pxとする。
# 73-03 多角点等（二重円 12.06px）とは輪の数で区別される。
D = 18.5
d = (ring(CX, CY, (D - W) / 2) +
     ring(CX, CY, (D * 1.5 / 2.5 - W) / 2) +
     ring(CX, CY, (D * 0.7 / 2.5 - W) / 2))
write('7306', d, f'三重の同心円 外径{D:.1f}/{D * 0.6:.1f}/{D * 0.28:.2f}px')

# =====================================================================
# 2026-08-13 追加分。建物等（レイヤ35）の未作成19件（#6 フェーズ2の第1弾）。
#
# 形は図式PDFのベクター描画から実測した。記号本体は線幅0.6pt、寸法の引出線は
# 0.15pt（多くは破線）で描かれているので、0.6pt の要素だけを拾えば本体が取れる。
# 以下のコメントの pt 値はその実測値。
#
# 大きさは docs/icon-authoring-guide.md の方針どおり mm 比の再現ではなく、
# **図式実測の最大寸法がインク22pxになる倍率**に揃えた。円だけの記号なら
# 外径22px＝既存の官公署系（3519/3525/3526/3536）と同径になる。
# =====================================================================

INK = 22.0            # インクの外形（既存の官公署系の円と同径）
GLYPH = 16.2          # ○の中の字の大きさ。3531 保 と同じ


def fit(w_pt, h_pt, ink=INK):
    """図式実測(pt)の外形を、インクが ink px に収まる倍率に直す。

    実測値はパスの中心線なので、両側に線幅の半分が乗る分を引いておく。"""
    return (ink - W) / max(w_pt, h_pt)


# ---- ○＋漢字の9件 ----------------------------------------------------
# 図式(p.67〜74): いずれも円φ4.0mm（2500用は2.5mm）の中に漢字1文字。
# 円は既存の3519/3531と同じ外径22px、字は3531 保と同じ16.2px。
# 「工」のような横長の字は長辺で合わせて円からはみ出さないようにする。
for code, ch, page in [('3512', '工', 67), ('3513', '出', 67), ('3517', '安', 68),
                       ('3518', '土', 68), ('3527', '博', 71), ('3528', '図', 71),
                       ('3529', '美', 71), ('3539', '百', 73), ('3552', '浄', 74)]:
    d = ring(CX, CY, (INK - W) / 2) + glyph_box(ch, GLYPH, CX, CY, weight=400)
    write(code, d, f'円22px＋「{ch}」{GLYPH}px（Noto Sans JP 400 / OFL・図式p{page}）')

# ---- 35-03 官公署 ----------------------------------------------------
# 図式(p.65): 円の上に短い軸、その左右に小円2つ。
# 実測(pt): 円φ8.43 / 小円φ1.65（中心は円の中心から左右±4.35・上5.91）/
#           軸2.44（円の上端から上へ）/ 全体 10.35×11.02。
k = fit(10.35, 11.02)
r_main, r_dot = 8.43 / 2 * k, 1.65 / 2 * k
dx, dy = 4.35 * k, 5.91 * k
stem = 2.44 * k
cy = CY + 1.22 * k                                  # 全体の中心から円の中心へのずれ
d = (ring(CX, cy, r_main - W / 2) +
     ring(CX - dx, cy - dy, r_dot - W / 2) +
     ring(CX + dx, cy - dy, r_dot - W / 2) +
     seg((CX, cy - r_main), (CX, cy - r_main - stem)))
write('3503', center_ink(d), f'円φ{r_main * 2:.1f}＋軸{stem:.1f}＋小円φ{r_dot * 2:.1f}px×2')

# ---- 35-04 裁判所 / 35-05 検察庁 -------------------------------------
# 図式(p.65): 三角形の下に短い支柱（立て札）。検察庁は三角形の中に横線2本が入り、
# 高さを3等分する。実測(pt): 裁判所 底辺12.46・高さ8.79・支柱3.41、
#                            検察庁 底辺12.33・高さ8.69・支柱3.38（横線は1/3と2/3）。
def tatefuda(base_pt, h_pt, stem_pt, bands=1):
    k = fit(base_pt, h_pt + stem_pt)
    base, h, stem = base_pt * k, h_pt * k, stem_pt * k
    y_base = CY + (h + stem) / 2 - stem                # 底辺の高さ
    apex = (CX, y_base - h)
    d = poly_band([(CX - base / 2, y_base), apex, (CX + base / 2, y_base)])
    d += seg((CX, y_base), (CX, y_base + stem))
    for i in range(1, bands):                          # 高さを bands 等分する横線
        y = y_base - h * i / bands
        w = base * (bands - i) / bands                 # 相似で決まる弦の長さ
        d += seg((CX - w / 2, y), (CX + w / 2, y))
    return d, base, h, stem


d, base, h, stem = tatefuda(12.46, 8.79, 3.41)
write('3504', center_ink(d), f'三角形{base:.1f}×{h:.1f}＋支柱{stem:.1f}px')
d, base, h, stem = tatefuda(12.33, 8.69, 3.38, bands=3)
write('3505', center_ink(d), f'三角形{base:.1f}×{h:.1f}＋支柱{stem:.1f}px・横線2本（3等分）')

# ---- 35-07 税務署 ----------------------------------------------------
# 図式(p.66): そろばんの玉。菱形の上下に軸が出る。
# 実測(pt): 菱形 12.40×7.36 / 軸 上2.45・下2.46 / 全体 12.40×12.27。
k = fit(12.40, 12.27)
dw, dh, ax = 12.40 * k, 7.36 * k, 2.45 * k
d = (poly_band([(CX, CY - dh / 2), (CX + dw / 2, CY), (CX, CY + dh / 2),
                (CX - dw / 2, CY)]) +
     seg((CX, CY - dh / 2), (CX, CY - dh / 2 - ax)) +
     seg((CX, CY + dh / 2), (CX, CY + dh / 2 + ax)))
write('3507', center_ink(d), f'菱形{dw:.1f}×{dh:.1f}＋上下の軸{ax:.1f}px')

# ---- 35-08 税関 / 35-11 測候所 ---------------------------------------
# 図式(p.66/67): 横棒＋中央の縦棒。税関は棒の内側に短い下向きの爪が2つ、
# 測候所は棒の両端に棒をまたぐ縦の爪が付く。
# 実測(pt): 税関  横棒12.29・縦棒11.85・爪1.30（下向き・端から1.62内側）
#           測候所 横棒12.39・縦棒12.36・爪2.57（両端・棒の上下に均等）
k = fit(12.29, 11.95)
bar, post, claw, inset = 12.29 * k, 11.85 * k, 1.30 * k, 1.62 * k
ytop = CY - 11.95 * k / 2
d = seg((CX - bar / 2, ytop), (CX + bar / 2, ytop)) + seg((CX, ytop), (CX, ytop + post))
for sx in (-1, 1):
    x = CX + sx * (bar / 2 - inset)
    d += seg((x, ytop), (x, ytop + claw))
write('3508', center_ink(d), f'横棒{bar:.1f}＋縦棒{post:.1f}＋下向きの爪{claw:.1f}px×2')

k = fit(12.64, 13.61)
bar, post, claw = 12.39 * k, 12.36 * k, 2.57 * k
ytop = CY - 13.61 * k / 2 + claw / 2                  # 爪が棒の上へ出る分だけ下げる
d = seg((CX - bar / 2, ytop), (CX + bar / 2, ytop)) + seg((CX, ytop), (CX, ytop + post))
for sx in (-1, 1):
    x = CX + sx * bar / 2
    d += seg((x, ytop - claw / 2), (x, ytop + claw / 2))
write('3511', center_ink(d), f'横棒{bar:.1f}＋縦棒{post:.1f}＋両端の爪{claw:.1f}px')

# ---- 35-24 学校 ------------------------------------------------------
# 図式(p.70): 「文」を直線で構図したもの。横棒の上に短い突起、下に交差する2本。
# 実測(pt): 横棒13.80 / 突起1.79（上へ）/ 斜線は横棒上の±4.14から下12.11の∓5.80へ。
k = fit(13.80, 13.71)
bar, tick = 13.80 * k, 1.79 * k
xin, xout, drop = 4.14 * k, 5.80 * k, 11.92 * k
ybar = CY - 13.71 * k / 2 + tick
d = (seg((CX - bar / 2, ybar), (CX + bar / 2, ybar)) +
     seg((CX, ybar), (CX, ybar - tick)) +
     seg((CX - xin, ybar), (CX + xout, ybar + drop)) +
     seg((CX + xin, ybar), (CX - xout, ybar + drop)))
write('3524', center_ink(d), f'「文」横棒{bar:.1f}＋突起{tick:.1f}＋交差2本（図式の直線構図）')

# ---- 35-49 発電所 ----------------------------------------------------
# 図式(p.74): 円から8方向に光。実測(pt) 円φ8.28、光は円の縁(r4.2)から
# 縦・斜めが r7.2、左右だけ r7.86 まで伸びる（全体 15.72×13.84）。
k = fit(15.72, 13.84)
r_in, r_v, r_h = 4.2 * k, 7.2 * k, 7.86 * k
d = ring(CX, CY, 8.28 / 2 * k - W / 2)
for i in range(8):
    a = math.radians(45 * i)
    r_out = r_h if i in (0, 4) else r_v               # 左右だけ長い
    d += seg((CX + r_in * math.cos(a), CY + r_in * math.sin(a)),
             (CX + r_out * math.cos(a), CY + r_out * math.sin(a)))
write('3549', center_ink(d), f'円φ{8.28 * k:.1f}＋光8本（左右{r_h:.1f}・他{r_v:.1f}px）')

# ---- 35-53 揚水機場 / 35-57 排水機場 ---------------------------------
# 図式(p.74/75): 台座線の上に半円（ドーム）、そこから3方向（上・左右斜め）に光。
# 排水機場はドームの中に横線2本が入り、高さを3等分する。ここだけが両者の違い。
# 実測(pt): 台座16.56 / ドーム r5.6・高さ5.7 / 光は縁から r8.2 まで / 全体16.56×8.14。
def kikaba(bands=1):
    k = fit(16.56, 8.14)
    base, r, r_out = 16.56 * k, 5.6 * k, 8.2 * k
    ybase = CY + 8.14 * k / 2
    d = (seg((CX - base / 2, ybase), (CX + base / 2, ybase)) +
         arc_band(CX, ybase, r, math.pi, 2 * math.pi))
    for deg in (225, 270, 315):
        a = math.radians(deg)
        d += seg((CX + r * math.cos(a), ybase + r * math.sin(a)),
                 (CX + r_out * math.cos(a), ybase + r_out * math.sin(a)))
    for i in range(1, bands):                          # ドームを bands 等分する弦
        y = r * i / bands
        half = math.sqrt(max(r * r - y * y, 0))
        d += seg((CX - half, ybase - y), (CX + half, ybase - y))
    return d, base, r, r_out


d, base, r, r_out = kikaba()
write('3553', center_ink(d), f'台座{base:.1f}＋半円r{r:.1f}＋光3本（r{r_out:.1f}px）')
d, base, r, r_out = kikaba(bands=3)
write('3557', center_ink(d), f'台座{base:.1f}＋半円r{r:.1f}＋光3本＋弦2本（3等分・3553との違い）')

# =====================================================================
# 2026-08-13 追加分その2。小物体（レイヤ42）の未作成19件（#6 フェーズ2の第2弾）。
#
# 形は図式PDFのベクター描画から実測した（35xx と同じ方法）。小物体の図式は
# 記号本体を 0.45pt で描いているものが多く、真形と極小記号が同じ欄に並ぶので、
# 点アイコンには極小記号の側を採る（41-17 地下換気孔の真形の外枠など）。
#
# 大きさは既存の小物体アイコンから校正した。図式の実測(pt)と icons/ の実測(px)を
# 突き合わせると px/pt は中央値 1.95（4101/4111 マンホール 1.8、4215 消火栓 2.2、
# 4241/4243 灯台・灯標 2.3、4132 電話柱 2.0）。そこで px/pt = 2.0 を基本とし、
# 最大寸法が22pxを超えるものだけ22pxに収める。
# =====================================================================

KOMONO = 2.0          # px/pt。既存の小物体アイコンからの校正値
CAP = 22.0            # これを超える寸法にはしない


def komono(w_pt, h_pt, s=KOMONO, cap=CAP):
    """小物体の図式実測(pt)を px の倍率に直す。"""
    return min(s, cap / max(w_pt, h_pt))


def T(pts, org, k):
    """図式の実測座標(pt)を、org を中心・倍率 k でキャンバス座標に移す。"""
    return [((x - org[0]) * k + CX, (y - org[1]) * k + CY) for x, y in pts]


# ---- 41-19 有線柱（点E5＋方向E6） ------------------------------------
# 図式(p.76): 円＋縦線＋架線2本。41-32 電話柱（円＋水平線）・41-42 電力柱の兄弟で、
# 円の大きさはそちらに合わせる（同系統で径が違うと読み分けられない）。ただし
# 架線の長さと縦線の位置は 4119 自身の図式実測による。円の外径5.13ptに対し
#   架線 = 円の縁から 0.861×外径（4132 は 1.0×外径で、ここが両者で違う）
#   縦線 = 円の中心から上へ 0.437×外径、下へ 0.675×外径（下だけ円から出る）
#   架線の角度 213.7°/341.3°（画面座標・Y下向き・右が0°）
# 取得位置は柱の中心なので円の中心を (32,32) に置く。
d = (ring(CX, CY, (D4132 - W) / 2) +
     seg((CX, CY - 0.437 * D4132), (CX, CY + 0.675 * D4132)) +
     haisen(D4132, 0.861 * D4132, 213.7) + haisen(D4132, 0.861 * D4132, 341.3))
write('4119', d, f'円 外径{D4132:.1f}px＋縦線＋架線2本 長さ{0.861 * D4132:.1f}px'
                f'(213.7°/341.3°)')

# ---- 42-06 狛犬（方向E6） --------------------------------------------
# 図式(p.80): 台座の矩形10.43×5.00pt の中に、横棒8.34＋両端の縦棒3.20。
# 方向レイヤなので図式のとおり水平に描く。
k = komono(10.43, 5.00)
(x0, y0), (x1, y1) = T([(286.53, 237.12), (296.96, 242.12)], (291.75, 239.62), k)
d = rect_band(x0 + W / 2, y0 + W / 2, x1 - W / 2, y1 - W / 2)
(bx0, by), (bx1, _) = T([(287.53, 239.52), (295.87, 239.52)], (291.75, 239.62), k)
d += seg((bx0, by), (bx1, by))
for x in (bx0, bx1):
    (_, cy0), (_, cy1) = T([(0, 238.00), (0, 241.20)], (291.75, 239.62), k)
    d += seg((x, cy0), (x, cy1))
write('4206', center_ink(d), f'台座{(x1 - x0):.1f}×{(y1 - y0):.1f}＋横棒＋両端の縦棒（右向き）')

# ---- 42-08 自然災害伝承碑（点E5） ------------------------------------
# 図式(p.81): 上が丸い碑（幅3.31・高7.08pt）＋中央の縦線、右へ延びる台座線6.63。
k = komono(6.63, 8.17)
org = (296.20, 150.38)
(sl, sb), (sr, st), (bl, _), (br, _), (ml, mt), (_, mb) = T(
    [(292.89, 153.92), (296.20, 146.84), (292.89, 0), (299.52, 0),
     (294.65, 152.40), (0, 147.65)], org, k)
r = (sr - sl) / 2
d = (seg((sl, sb), (sl, st)) + seg((sr, sb), (sr, st)) +
     arc_band(sl + r, st, r, math.pi, 2 * math.pi) +
     seg((ml, mt), (ml, mb)) + seg((bl, sb), (br, sb)))
write('4208', center_ink(d), f'丸屋根の碑 幅{r * 2:.1f}×高{sb - st:.1f}＋台座線{br - bl:.1f}px')

# ---- 42-11 官民境界杭（点E5） ----------------------------------------
# 図式(p.81): 正方形8.64×8.48pt の中に、内側へ1.33寄せたX。
k = komono(8.64, 8.48)
org = (294.15, 300.87)
(x0, y0), (x1, y1), (ax0, ay0), (ax1, ay1) = T(
    [(289.83, 296.63), (298.47, 305.11), (291.16, 297.94), (297.14, 303.81)], org, k)
d = (rect_band(x0 + W / 2, y0 + W / 2, x1 - W / 2, y1 - W / 2) +
     seg((ax0, ay0), (ax1, ay1)) + seg((ax1, ay0), (ax0, ay1)))
write('4211', center_ink(d), f'正方形{x1 - x0:.1f}px＋内側のX')

# ---- 42-17 地下換気孔（点E5） ----------------------------------------
# 図式(p.81): 真形の外枠（22.17×10.79pt）の中に極小記号。点アイコンには
# 極小記号だけを採る。斜線2本×2組（±45度）が格子になっている。
k = komono(7.87, 8.08)
org = ((295.50 + 303.37) / 2, (405.88 + 413.96) / 2)
d = ''
for a, b in [((298.25, 405.88), (303.37, 410.95)), ((295.50, 408.55), (300.63, 413.62)),
             ((298.37, 413.96), (303.30, 408.97)), ((295.60, 410.91), (300.53, 405.92))]:
    p0, p1 = T([a, b], org, k)
    d += seg(p0, p1)
write('4217', center_ink(d), '格子（±45度の斜線を2本ずつ）')

# ---- 42-23 噴水（点E5） ----------------------------------------------
# 図式(p.83): 水盤の楕円11.27×6.38pt、中央の水柱7.06、頂部に小さな楕円2つ
# （3.90×3.26、左右に並ぶ）。
k = komono(11.27, 11.35)
org = (297.82, (138.73 + 150.08) / 2)
(bx, by), (jt_x, jt_y), (jb_x, jb_y), (lx, ly), (rx, ry) = T(
    [(297.82, 146.89), (297.75, 140.36), (297.75, 147.42),
     (295.80, 140.36), (299.69, 140.36)], org, k)
brx, bry = 11.27 / 2 * k, 6.38 / 2 * k
srx, sry = 3.90 / 2 * k, 3.26 / 2 * k
d = ellipse_band(bx, by, brx, bry) + seg((jt_x, jt_y), (jb_x, jb_y))
for cx_ in (lx, rx):
    d += ellipse_band(cx_, ly, srx, sry)
write('4223', center_ink(d), f'水盤の楕円{brx * 2:.1f}×{bry * 2:.1f}＋水柱＋噴出の楕円2つ')

# ---- 42-24 井戸 / 42-26 貯水槽 / 42-27 肥料槽 / 42-45 ヘリポート ------
# いずれも円の中に文字。図式実測(pt)は
#   井戸    円6.85・「井」5.38（円の0.79）
#   貯水槽  円10.49・「W」6.22（0.59）
#   肥料槽  円10.50・「ヒ」6.62（0.63）
#   ヘリポート 円20.34・「H」（円の0.55と読む）
for code_, ch, dia_pt, ratio in [('4224', '井', 6.85, 0.79), ('4226', 'W', 10.49, 0.59),
                                 ('4227', 'ヒ', 10.50, 0.63), ('4245', 'H', 20.34, 0.55)]:
    k = komono(dia_pt, dia_pt)
    dia = dia_pt * k
    d = ring(CX, CY, (dia - W) / 2) + glyph_box(ch, dia * ratio, CX, CY, weight=400)
    write(code_, d, f'円φ{dia:.1f}px＋「{ch}」{dia * ratio:.1f}px（Noto Sans JP 400 / OFL）')

# ---- 42-25 油井・ガス井（点E5） --------------------------------------
# 図式(p.83): 井桁。縦2本・横2本が交差し、端が外へ出る（10.91×10.88pt）。
k = komono(10.91, 10.88)
org = ((290.17 + 301.08) / 2, (277.50 + 288.38) / 2)
d = ''
for a, b in [((291.81, 277.50), (291.81, 288.38)), ((299.45, 277.50), (299.45, 288.38)),
             ((290.17, 279.14), (301.08, 279.14)), ((290.17, 286.75), (301.08, 286.75))]:
    p0, p1 = T([a, b], org, k)
    d += seg(p0, p1)
write('4225', center_ink(d), '井桁（縦2本・横2本）')

# ---- 42-32 給水塔（点E5） --------------------------------------------
# 図式(p.84): 円φ7.38pt に、縦線と斜線2本が貫いて6本のスポークになる。
k = komono(8.64, 11.04)
org = (297.11, 407.05)
d = ring(CX, CY, (7.38 * k - W) / 2)
for a, b in [((297.11, 401.74), (297.11, 412.78)), ((292.58, 403.37), (301.22, 410.73)),
             ((292.58, 410.73), (301.22, 403.78))]:
    p0, p1 = T([a, b], org, k)
    d += seg(p0, p1)
write('4232', center_ink(d), f'円φ{7.38 * k:.1f}px＋貫く3本（6本スポーク）')

# ---- 42-33 火の見（点E5） --------------------------------------------
# 図式(p.85): 右端の柱9.80pt に横腕9.93が付き、腕の左端から小円φ1.64が吊り下がる。
k = komono(9.93, 9.80)
org = ((291.31 + 301.24) / 2, (145.19 + 154.99) / 2)
(al, ay), (ar, _), (px, pt_), (_, pb), (hx, ht), (_, hb) = T(
    [(291.31, 147.64), (301.24, 147.64), (299.17, 145.19), (0, 154.99),
     (292.55, 147.64), (0, 149.27)], org, k)
bell_r = 1.64 / 2 * k
d = (seg((al, ay), (ar, ay)) + seg((px, pt_), (px, pb)) +
     seg((hx, ht), (hx, hb)) + ring(hx, hb + bell_r, bell_r - W / 2))
write('4233', center_ink(d), f'柱＋横腕{ar - al:.1f}＋吊り下げた小円φ{bell_r * 2:.1f}px')

# ---- 42-42 航空灯台（点E5） ------------------------------------------
# 図式(p.87): 光を放つ円（円φ4.79・中心の点φ1.10・光8本）の上に小さな箱2つ
# （3.89×2.01pt を左右に）。
k = komono(9.97, 13.12)
org = ((294.63 + 304.60) / 2, (269.82 + 282.94) / 2)
(sx, sy) = T([(299.38, 278.27)], org, k)[0]
d = ring(sx, sy, (4.79 * k - W) / 2) + dot(sx, sy, 1.10 / 2 * k)
for a, b in [((299.42, 275.95), (299.42, 273.84)), ((299.42, 282.94), (299.42, 280.83)),
             ((296.85, 278.39), (294.63, 278.39)), ((304.21, 278.39), (301.99, 278.39)),
             ((297.66, 276.71), (296.01, 275.22)), ((301.19, 276.71), (302.83, 275.22)),
             ((296.01, 281.59), (297.66, 280.12)), ((303.19, 281.26), (301.54, 279.77))]:
    p0, p1 = T([a, b], org, k)
    d += seg(p0, p1)
for a, b in [((294.63, 269.82), (298.52, 271.83)), ((300.71, 269.82), (304.60, 271.83))]:
    (bx0, by0), (bx1, by1) = T([a, b], org, k)
    d += rect_band(bx0 + W / 2, by0 + W / 2, bx1 - W / 2, by1 - W / 2)
write('4242', center_ink(d), f'光を放つ円φ{4.79 * k:.1f}＋中心の点＋上の箱2つ')

# ---- 42-52 流量観測所（点E5） ----------------------------------------
# 図式(p.88): 正方形8.68×8.57pt の中に、3等分された箱4.95×5.31。
k = komono(8.68, 8.57)
org = ((291.32 + 300.00) / 2, (245.16 + 253.73) / 2)
(ox0, oy0), (ox1, oy1), (ix0, iy0), (ix1, iy1) = T(
    [(291.32, 245.16), (300.00, 253.73), (292.98, 246.79), (297.93, 252.10)], org, k)
d = (rect_band(ox0 + W / 2, oy0 + W / 2, ox1 - W / 2, oy1 - W / 2) +
     rect_band(ix0 + W / 2, iy0 + W / 2, ix1 - W / 2, iy1 - W / 2))
for yy in (248.83, 250.46):
    (_, ly) = T([(0, yy)], org, k)[0]
    d += seg((ix0, ly), (ix1, ly))
write('4252', center_ink(d), '正方形＋内側の箱（横線2本で3等分）')

# ---- 42-53 雨量観測所（点E5） ----------------------------------------
# 図式(p.88): 二重円（8.57/5.50pt）を横線12.01が貫き、内円の中に横線2本。
k = komono(12.01, 8.58)
org = (295.29, 310.63)
d = ring(CX, CY, (8.57 * k - W) / 2) + ring(CX, CY, (5.50 * k - W) / 2)
(lx0, ly), (lx1, _) = T([(289.25, 310.74), (301.26, 310.74)], org, k)
d += seg((lx0, ly), (lx1, ly))
for yy in (309.42, 311.95):
    (ix0, iy), (ix1, _) = T([(293.05, yy), (297.39, yy)], org, k)
    d += seg((ix0, iy), (ix1, iy))
write('4253', center_ink(d), f'二重円{8.57 * k:.1f}/{5.50 * k:.1f}＋貫く横線＋内側の横線2本')

# ---- 42-54 水質観測所（点E5） ----------------------------------------
# 図式(p.88): 円φ8.62pt の中に下向きの三角形（7.35×5.76）。
k = komono(8.68, 8.56)
org = (297.31, 376.73)
d = ring(CX, CY, (8.62 * k - W) / 2)
tri = T([(293.47, 374.64), (300.82, 374.64), (297.14, 380.40)], org, k)
d += poly_band(tri)
write('4254', center_ink(d), f'円φ{8.62 * k:.1f}px＋下向きの三角形')

# ---- 42-55 波浪観測所（点E5） ----------------------------------------
# 図式(p.88): 水平線を横切るS字の波。この記号だけ図式が0.9pt（他の小物体の倍）で
# 描かれていて、基準の1.1pxに落とすと実表示でほとんど見えなくなるため、図式の
# とおり倍の太さで引く。
k = komono(10.79, 4.09)
WAVE = 0.9 * k
org = ((290.06 + 300.85) / 2, (434.04 + 438.13) / 2)
d = seg(*T([(290.51, 436.38), (300.76, 436.38)], org, k), w=WAVE)
for chain in [[(300.85, 438.13), (300.31, 437.53), (299.80, 437.19), (299.22, 436.86),
               (298.42, 436.64), (296.84, 436.47), (295.47, 436.41)],
              [(290.06, 434.04), (290.60, 434.78), (291.10, 435.19), (291.69, 435.61),
               (292.48, 435.87), (294.07, 436.07), (295.44, 436.16)]]:
    d += polyline(T(chain, org, k), w=WAVE)
write('4255', center_ink(d), f'水平線を横切るS字の波（線幅{WAVE:.1f}px・図式が0.9ptのため）')

# ---- 42-56 風向・風速観測所（点E5） ----------------------------------
# 図式(p.89): 二重円（8.57/5.14pt）を斜線16.68が貫く（右上から左下へ）。
k = komono(11.83, 11.76)
org = (295.83, 148.56)
d = ring(CX, CY, (8.57 * k - W) / 2) + ring(CX, CY, (5.14 * k - W) / 2)
d += seg(*T([(301.31, 143.08), (289.48, 154.84)], org, k))
write('4256', center_ink(d), f'二重円{8.57 * k:.1f}/{5.14 * k:.1f}＋貫く斜線')

# ---- 22-35 雨水桝（方向E6） ------------------------------------------
# 図式には面（E1）としか定義がないコード。実データでは方向（E6）で入り、豊中市の
# 道路台帳平面図DM500では最多のコードになる（shiwaku/dm-sprite#4）。そのため意匠は
# 図式ではなく納品図面の実測による。#4 のコメントの実測値:
#   枠だけの正方形（塗りなし）・外形0.60m角・記号の向きに沿って0.72m
#   （0.60が輪郭の中心線、0.72がインクと読める。差0.12m=線幅の両側ぶん）
#   1:500 の紙の上で約1.4mm角。代表点は図形の中心（±0.2m以内）
# 大きさは既存アイコンとの相対で決めた。マンホール極小φ2.0mm=実寸1.0mが18.56pxなので、
# 0.60m角なら 18.56*0.6 = 11.1px。9.3px/mm換算（1.4mm角→13.0px）ともほぼ揃う。
# 紙の比率どおりに 4〜6px まで落とすと枠の内側が1px未満になって点に潰れるため採らない
# （8199 指示点が5.94pxで成立するのは塗りつぶしの丸だから）。
# 方向レイヤだが正方形は90度対称なので Angle での回転はほとんど見えない。
D2235 = 11.2                                  # インクの外形
d = rect_band(CX - (D2235 - W) / 2, CY - (D2235 - W) / 2,
              CX + (D2235 - W) / 2, CY + (D2235 - W) / 2)
write('2235', d, f'枠だけの正方形 外形{D2235:.1f}px（図面実測0.60m角・回転しても同じ形）')


# =====================================================================
# 2026-08-13 追加分その3。土地利用等（レイヤ62/63）のうち、図式の座標が取れた7件
# （#6 フェーズ2の第3弾）。残る8件は図式が線を持たない塗りだけで描かれていて
# （空地・花壇・採石場・土取場・採鉱地）、または面を埋めるパターン（干潟・砂地・
# れき地）なので、読み取り方を別に決めてから作図する。
#
# 土地利用等の記号は 0.3pt の細い線で描かれている（建物等0.6・小物体0.45）。
# 大きさは既存の62xx/63xxアイコンから校正した px/pt = 1.7（中央値。6311 田1.53・
# 6313 畑1.72・6331 広葉樹林1.83・6334 荒地1.62 など）。22pxを上限にする。
#
# 曲線が主体の3件（陵墓・わさび畑・噴火口）は trace() で図式の座標を写した。
# 照合が自己参照になるので、図式画像と並べた目視で確認している。
# =====================================================================

CHIRI = 1.7           # px/pt。既存の土地利用等アイコンからの校正値


def chiri(w_pt, h_pt, cap=CAP):
    return min(CHIRI, (cap - W) / max(w_pt, h_pt))


# ---- 62-24 古墳（点E5） ----------------------------------------------
# 図式(p.109): 円φ4.74pt の下に三角形（底辺6.54・高さ7.34）。前方後円墳の形。
k = chiri(6.54, 10.17)
org = ((295.86 + 302.40) / 2, (188.45 + 198.62) / 2)
(ccx, ccy), (apex), (bl), (br) = T([(299.10, 190.81), (299.13, 191.28),
                                    (295.86, 198.62), (302.40, 198.62)], org, k)
d = ring(ccx, ccy, (4.74 * k - W) / 2) + poly_band([apex, br, bl])
write('6224', center_ink(d), f'円φ{4.74 * k:.1f}＋三角形（前方後円墳）')

# ---- 63-12 はす田（点E5） --------------------------------------------
# 図式(p.110): 楕円6.91×3.40pt の下端から茎3.22。
k = chiri(6.91, 6.64)
org = (291.43, (331.59 + 338.23) / 2)
(ex, ey), (s0), (s1) = T([(291.43, 333.29), (291.35, 335.01), (291.35, 338.23)], org, k)
d = ellipse_band(ex, ey, 6.91 / 2 * k, 3.40 / 2 * k) + seg(s0, s1)
write('6312', center_ink(d), f'楕円{6.91 * k:.1f}×{3.40 * k:.1f}＋茎{3.22 * k:.1f}px')

# ---- 63-15 パイナップル畑（点E5） ------------------------------------
# 図式(p.111): V字（下端から左右へ9.0pt）＋その中に円φ3.32。
k = chiri(11.59, 6.92)
org = ((288.84 + 300.43) / 2, (193.34 + 200.26) / 2)
(v), (vl), (vr), (cc) = T([(294.60, 200.26), (288.84, 193.34), (300.43, 193.34),
                           (294.60, 194.96)], org, k)
d = seg(v, vl) + seg(v, vr) + ring(cc[0], cc[1], (3.32 * k - W) / 2)
write('6315', center_ink(d), f'V字＋円φ{3.32 * k:.1f}px')

# ---- 62-25 城・城跡（点E5） ------------------------------------------
# 図式(p.109): 矩形2つ。上に5.11×3.22pt、下に15.34×6.33pt（城の輪郭）。
k = chiri(15.34, 9.63)
org = ((292.54 + 307.88) / 2, (225.98 + 235.61) / 2)
d = ''
for a, b in [((297.67, 225.98), (302.78, 229.20)), ((292.54, 229.28), (307.88, 235.61))]:
    (rx0, ry0), (rx1, ry1) = T([a, b], org, k)
    d += rect_band(rx0 + W / 2, ry0 + W / 2, rx1 - W / 2, ry1 - W / 2)
write('6225', center_ink(d), f'矩形2つ（上{5.11 * k:.1f}×{3.22 * k:.1f}・下{15.34 * k:.1f}×{6.33 * k:.1f}px）')

# ---- 62-21 噴火口・噴気口 / 62-23 陵墓 / 63-16 わさび畑 --------------
# 曲線が主体なので trace() で図式の座標を写す（座標写し）。
# 62-21(p.108): 火口の楕円＋中の横線2本＋上に立ちのぼる横線3本
# 62-23(p.109): 縦線＋横線2本＋左右に広がる曲線（墳丘の裾）
# 63-16(p.111): 円＋そこから垂れる曲線＋底の横線（わさびの株）
Z6221 = [
    ('l', [(295.46, 125.62), (300.43, 125.62)]), ('l', [(295.03, 128.06), (300.00, 128.06)]),
    ('l', [(294.24, 130.08), (300.00, 130.08)]),
    ('re', [(292.94, 130.94), (300.43, 132.53)]),
    ('c', [(291.29, 133.75), (291.29, 132.40), (293.71, 131.30), (296.69, 131.30)]),
    ('c', [(296.69, 131.30), (299.67, 131.30), (302.09, 132.40), (302.09, 133.75)]),
    ('l', [(293.81, 132.17), (300.00, 132.17)]),
    ('c', [(302.09, 133.75), (302.09, 135.10), (299.67, 136.20), (296.69, 136.20)]),
    ('c', [(296.69, 136.20), (293.71, 136.20), (291.29, 135.10), (291.29, 133.75)]),
    ('l', [(292.94, 134.18), (300.00, 134.18)]),
]
Z6223 = [
    ('l', [(299.45, 127.02), (299.45, 137.31)]), ('l', [(296.10, 127.08), (302.97, 127.08)]),
    ('c', [(306.23, 137.25), (304.40, 137.25), (302.92, 133.90), (302.92, 129.77)]),
    ('l', [(296.05, 129.88), (302.92, 129.88)]),
    ('c', [(292.85, 137.36), (294.67, 137.36), (296.16, 134.01), (296.16, 129.88)]),
]
Z6316 = [
    ('c', [(290.93, 260.68), (290.93, 259.54), (291.94, 258.62), (293.20, 258.62)]),
    ('c', [(293.20, 258.62), (294.45, 258.62), (295.46, 259.54), (295.46, 260.68)]),
    ('c', [(295.46, 260.68), (295.46, 261.81), (294.45, 262.73), (293.20, 262.73)]),
    ('c', [(293.20, 262.73), (291.94, 262.73), (290.93, 261.81), (290.93, 260.68)]),
    ('c', [(293.74, 262.73), (292.18, 262.76), (290.93, 264.00), (290.93, 265.51)]),
    ('l', [(290.93, 265.54), (296.26, 265.54)]),
]
for code_, items_, ink_, note_ in [
        ('6221', Z6221, 10.80 * CHIRI, '火口の楕円＋横線（座標写し）'),
        ('6223', Z6223, 13.85 * CHIRI, '縦線＋横線2本＋裾の曲線（座標写し）'),
        ('6316', Z6316, 6.92 * CHIRI, '円＋垂れる曲線＋底の横線（座標写し）')]:
    write(code_, center_ink(trace(items_, min(ink_, CAP))), note_)


print(f'\n出力先: {OUT}')

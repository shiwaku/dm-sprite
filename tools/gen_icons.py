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

print(f'\n出力先: {OUT}')

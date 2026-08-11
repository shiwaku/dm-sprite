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
# 末尾は 2026-08 に追加した6コードの作図例。新しい記号を足すときは
# 同じ書き方で write(...) を1行ずつ増やす。
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


# 字入り記号（○＋漢字など）に使う書体。SIL OFL なので MIT の本リポジトリに取り込める。
FONT_CANDIDATES = [
    '/mnt/c/Windows/Fonts/NotoSansJP-VF.ttf',
    'C:/Windows/Fonts/NotoSansJP-VF.ttf',
    '/usr/share/fonts/opentype/noto/NotoSansJP[wght].ttf',
    os.path.expanduser('~/.fonts/NotoSansJP-VF.ttf'),
]


def glyph(ch, height, cx, cy, weight=400):
    """Noto Sans JP（OFL）から1文字のアウトラインを取り出し、指定サイズ・中心に配置。"""
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.transformPen import TransformPen

    path = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if path is None:
        raise FileNotFoundError(
            'Noto Sans JP が見つかりません。FONT_CANDIDATES にパスを追加してください。')
    font = instancer.instantiateVariableFont(TTFont(path), {'wght': weight})
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

print(f'\n出力先: {OUT}')

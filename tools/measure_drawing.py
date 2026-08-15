# -----------------------------------------
# 納品図面のPDFから、拡張DMコードの記号の意匠と寸法を実測する。
#
#   python3 tools/measure_drawing.py --pdf 図面.pdf --points 記号.geojson 4143 4145
#   python3 tools/measure_drawing.py ... --spec 4145        # 1件の幾何を外形比で分解
#   python3 tools/measure_drawing.py ... --crop out/        # 記号の切り出し画像を出す
#   python3 tools/measure_drawing.py ... --calibrate        # 既知コードで測り方を検算
#
# **標準図式のコードには使わない。** 図式に定義があるものは data/zushiki-geometry.json
# から起こし、tools/verify_shapes.py で照合する。この道具は図式に定義が無い拡張DM
# コード専用で、意匠の根拠が納品図面しか無い場合に使う。
#
# 何をしているか:
#
#   DMの代表点（経緯度）→ 平面直角座標 → 図枠のグリッドラベルから作った一次式で
#   PDFの紙面座標へ戻す → その位置の記号を取り出して測る
#
# 図面の点記号は**円も中の文字も1つの塗りパス**にまとまっているので、代表点にいちばん
# 近い塗りパス（bbox が --max-dim 以下のもの）を取れば記号1件が丸ごと手に入る。道路の
# 線・面は bbox が大きいので落ちる。窓の中の全パスをまとめて測ると近くの地物を拾う。
#
# **測り方は必ず既知のコードで検算してから使う（--calibrate）。** 豊中市の図郭57-08 では
# 41-91 が 0.773m・41-51 マンホール（下水）が 1.058m で、issue #22 の実測（0.778 / 1.069）
# と一致する。図郭やベンダが変わればグリッドラベルの読み方から変わる。
#
# 依存: pymupdf / numpy / pyproj（緯度経度→平面直角座標）/ Pillow（--crop のみ）
# -----------------------------------------
import json
import math
import os
import re
import sys
from collections import Counter

import fitz
import numpy as np

# マンホール極小 φ2.0mm＝地上1.0m が 18.56px。既存アイコンから校正した換算率で、
# 図面の実寸を px の見当に直すのに使う（採用サイズは同系統の既存アイコンに揃える。
# docs/icon-authoring-guide.md「3. 大きさを決める」）。
PX_PER_M = 18.56

DEFAULT_EPSG = 6674          # 平面直角座標系 VI（近畿）
MAX_DIM_M = 2.0              # これより大きい bbox のパスは地物とみなす
MAX_OFF_M = 0.45             # 代表点からパス中心までの許容
MAX_N = 40                   # 1コードあたりの計測件数
MIN_HORIZ = 0.03             # 水平線とみなす最短の長さ（外形比）。円の縁の短い弦を拾わない


def die(msg):
    sys.exit(f'measure_drawing: {msg}')


# ---- 図枠を読んで PDF pt → 平面直角座標 の一次式を作る ----

def grid_labels(page):
    """図枠の座標ラベルを (中心x, 中心y, 値) で集める。"""
    out = []
    for w in page.get_text('words'):
        if re.fullmatch(r'-?[0-9,]{5,9}', w[4]):
            out.append(((w[0] + w[2]) / 2, (w[1] + w[3]) / 2,
                        int(w[4].replace(',', ''))))
    return out


def _fit_axis(labels, axis, tol_m=0.5):
    """紙面座標と座標値が一次に並ぶラベルの最大の集まりを探して (傾き, 切片) を返す。

    図面には図郭番号や地番など座標でない数字も入るので、範囲で決め打ちすると図郭が
    変わったときに外れる。グリッドラベルだけが厳密に一次に並ぶ性質を使い、2点ずつ
    直線を立てて、それに乗るラベルがいちばん多い組を採る（RANSAC）。
    """
    k = 0 if axis == 'x' else 1
    pts = [(p[k], p[2]) for p in labels]
    best = None
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            (x0, v0), (x1, v1) = pts[i], pts[j]
            if abs(x1 - x0) < 1.0 or v0 == v1:
                continue
            a = (v1 - v0) / (x1 - x0)
            b = v0 - a * x0
            inl = [p for p in pts if abs(p[1] - (a * p[0] + b)) < tol_m]
            if best is None or len(inl) > len(best[0]):
                best = (inl, a, b)
    if best is None or len(best[0]) < 3:
        return None
    inl = best[0]
    a, b = np.polyfit([p[0] for p in inl], [p[1] for p in inl], 1)
    return float(a), float(b), len(inl)


def affine(page):
    """(a_e, b_e, a_n, b_n) を返す。easting = x*a_e + b_e、northing = y*a_n + b_n。"""
    labels = grid_labels(page)
    if len(labels) < 6:
        die('図枠の座標ラベルを読めませんでした。PDFが想定と違います')
    ew = _fit_axis(labels, 'x')
    ns = _fit_axis(labels, 'y')
    if ew is None or ns is None:
        die('グリッドラベルが一次に並ぶ組を見つけられませんでした')
    a_e, b_e, n_ew = ew
    a_n, b_n, n_ns = ns
    if not 0.8 < abs(a_e / a_n) < 1.25:
        die(f'東西と南北で縮尺が合いません（{abs(1 / a_e):.3f} / {abs(1 / a_n):.3f} pt/m）。'
            'ラベルの読み分けが外れている可能性があります')
    return float(a_e), float(b_e), float(a_n), float(b_n)


# ---- 記号1件を取り出す ----

def item_points(it):
    pts = []
    for q in it[1:]:
        if hasattr(q, 'x'):
            pts.append((q.x, q.y))
        elif hasattr(q, 'ul'):
            pts += [(q.ul.x, q.ul.y), (q.lr.x, q.lr.y)]
    return pts


class Drawing:
    """図面PDF1枚ぶん。代表点から記号の塗りパスを引ける。"""

    def __init__(self, pdf, page_no=0, epsg=DEFAULT_EPSG, max_dim=MAX_DIM_M):
        self.doc = fitz.open(pdf)
        self.page = self.doc[page_no]
        self.a_e, self.b_e, self.a_n, self.b_n = affine(self.page)
        self.pt_per_m = abs(1.0 / self.a_e)
        self.epsg = epsg
        self.paths, centers = [], []
        for dr in self.page.get_drawings():
            r = dr['rect']
            if max(r.width, r.height) / self.pt_per_m > max_dim:
                continue
            self.paths.append(dr)
            centers.append(((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2))
        self.centers = np.array(centers) if centers else np.zeros((0, 2))

    def to_page(self, lon, lat):
        """経緯度 → PDF の紙面座標。"""
        try:
            from pyproj import Transformer
        except ImportError:
            die('pyproj が要ります（pip install pyproj）')
        if not hasattr(self, '_tr'):
            self._tr = Transformer.from_crs('EPSG:4326', f'EPSG:{self.epsg}',
                                            always_xy=True)
        e, n = self._tr.transform(lon, lat)
        return (e - self.b_e) / self.a_e, (n - self.b_n) / self.a_n

    def symbol_at(self, lon, lat, max_off=MAX_OFF_M):
        """代表点にいちばん近い塗りパス。遠ければ None。"""
        if not len(self.centers):
            return None
        px, py = self.to_page(lon, lat)
        d = np.hypot(self.centers[:, 0] - px, self.centers[:, 1] - py) / self.pt_per_m
        i = int(np.argmin(d))
        if d[i] > max_off:
            return None
        return self.paths[i], (px, py)


# ---- 点データ（DM→GeoJSON）----

def load_points(paths, field):
    """{コード: [(経度, 緯度, 出どころ), ...]}"""
    out = {}
    for p in paths:
        with open(p, encoding='utf-8') as fp:
            gj = json.load(fp)
        tag = os.path.splitext(os.path.basename(p))[0]
        for f in gj.get('features', []):
            code = str(f['properties'].get(field, '')).strip()
            g = f.get('geometry') or {}
            c = g.get('coordinates')
            if not code or not c:
                continue
            lon, lat = (c if g['type'] == 'Point' else c[0])[:2]
            out.setdefault(code, []).append((lon, lat, tag))
    return out


# ---- 1. 実測 ----

def measure(dw, points, codes):
    for code in codes:
        got = points.get(code, [])[:MAX_N]
        ws, hs, nseg, tags = [], [], [], set()
        for lon, lat, tag in got:
            hit = dw.symbol_at(lon, lat)
            if hit is None:
                continue
            dr, _ = hit
            r = dr['rect']
            ws.append(r.width / dw.pt_per_m)
            hs.append(r.height / dw.pt_per_m)
            nseg.append(sum(len(it) - 1 for it in dr['items']))
            tags.add(tag)
        if not ws:
            print(f'\n=== {code}  該当する塗りパスなし（{len(got)}件を探索）')
            continue
        w, h = float(np.median(ws)), float(np.median(hs))
        print(f'\n=== {code}  {len(ws)}/{len(got)}件  {sorted(tags)}')
        print(f'  外形 {w:.3f} × {h:.3f} m  →  {w * PX_PER_M:.1f} × {h * PX_PER_M:.1f} px'
              f'（{PX_PER_M} px/m 換算）')
        print(f'  外形のばらつき W {min(ws):.3f}〜{max(ws):.3f} m')
        print(f'  パスの線分数 {Counter(nseg).most_common(3)}')


# ---- 2. 幾何の分解（作図仕様）----

def spec(dw, points, codes, samples=1):
    """代表インスタンスの幾何を外形で正規化して出す。

    円は半径の峰に、ハッチは水平な線分の y に出る。塗りの帯（＝線）は上端と下端が
    2本の線として出るので、本数は「対になった y の組」で数える。
    """
    for code in codes:
        for lon, lat, tag in points.get(code, [])[:samples]:
            hit = dw.symbol_at(lon, lat)
            if hit is None:
                continue
            dr, _ = hit
            r = dr['rect']
            S = max(r.width, r.height)
            cx, cy = (r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2
            print(f'\n=== {code} ({tag})  外形 {r.width / dw.pt_per_m:.3f}×'
                  f'{r.height / dw.pt_per_m:.3f} m  項目{len(dr["items"])}')
            rad, horiz, other = Counter(), [], []
            for it in dr['items']:
                pts = [((p[0] - cx) / S, (p[1] - cy) / S) for p in item_points(it)]
                for p0, p1 in zip(pts, pts[1:]):
                    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
                    ln = math.hypot(dx, dy)
                    if ln < 1e-6:
                        continue
                    if abs(dy) < 0.004 and ln > MIN_HORIZ:
                        horiz.append(round((p0[1] + p1[1]) / 2, 3))
                    else:
                        other.append((ln, math.degrees(math.atan2(dy, dx))))
                    for p in (p0, p1):
                        rad[round(math.hypot(*p), 2)] += 1
            print('  半径の峰（外形比）', rad.most_common(5))
            if horiz:
                # 同じ y の線分をまとめる（1本の線が複数の線分に割れていることがある）
                ys, cl = sorted(horiz), []
                for y in ys:
                    if cl and abs(y - cl[-1][-1]) < 0.008:
                        cl[-1].append(y)
                    else:
                        cl.append([y])
                cs = [round(sum(g) / len(g), 3) for g in cl]
                print(f'  水平線 {len(cs)}本 → y（外形比）{cs}')
                # 図面の線は塗りの帯なので、上端と下端が2本に出る。隣り合う2本を
                # 1本とみなした中心が、作図で使うハッチの位置。
                pair = [round((cs[i] + cs[i + 1]) / 2, 4)
                        for i in range(0, len(cs) - 1, 2)]
                odd = '（端数1本あり）' if len(cs) % 2 else ''
                print(f'  帯の中心（＝ハッチ{len(pair)}本）{pair}{odd}')
            if other:
                top = sorted(other, key=lambda t: -t[0])[:5]
                print('  その他の線分（長さ, 角度）',
                      [(round(l, 3), round(a)) for l, a in top])


# ---- 3. 切り出し画像 ----

def crop(dw, points, codes, outdir, zoom=560, margin=0.12, samples=1):
    try:
        from PIL import Image
    except ImportError:
        die('Pillow が要ります（pip install pillow）')
    os.makedirs(outdir, exist_ok=True)
    for code in codes:
        for i, (lon, lat, _) in enumerate(points.get(code, [])[:samples]):
            hit = dw.symbol_at(lon, lat)
            if hit is None:
                continue
            dr, _ = hit
            r = dr['rect']
            m = margin * max(r.width, r.height) + 0.5
            clip = fitz.Rect(r.x0 - m, r.y0 - m, r.x1 + m, r.y1 + m)
            k = zoom / max(clip.width, clip.height)
            pm = dw.page.get_pixmap(matrix=fitz.Matrix(k, k), clip=clip)
            path = os.path.join(outdir, f'{code}-{i}.png')
            Image.frombytes('RGB', (pm.width, pm.height), pm.samples).save(path)
            print(f'{path}  外形 {r.width / dw.pt_per_m:.3f}×'
                  f'{r.height / dw.pt_per_m:.3f} m')


# ---- 4. 検算 ----

def calibrate(dw, points, expect):
    """既知コードの外形を測って期待値と比べる。ずれていたら終了コード1。"""
    print(f'図面の縮尺 {dw.pt_per_m:.4f} pt/m')
    bad = False
    for code, want in expect:
        got = points.get(code, [])[:MAX_N]
        ws = []
        for lon, lat, _ in got:
            hit = dw.symbol_at(lon, lat)
            if hit is not None:
                ws.append(hit[0]['rect'].width / dw.pt_per_m)
        if not ws:
            print(f'  {code}  測定できず（期待 {want:.3f} m）')
            bad = True
            continue
        w = float(np.median(ws))
        ok = abs(w - want) / want < 0.03
        print(f'  {code}  {w:.3f} m（期待 {want:.3f} m・{len(ws)}件）'
              f'  {"一致" if ok else "★ずれています"}')
        bad = bad or not ok
    if bad:
        sys.exit('検算に失敗しました。この図面ではこの測り方をそのまま使えません')
    print('検算に通りました。')


def main():
    args = sys.argv[1:]

    def opt(name, default=None):
        if name in args:
            i = args.index(name)
            return args[i + 1]
        return default

    pdf = opt('--pdf')
    pts = opt('--points')
    if not pdf or not pts:
        die('--pdf と --points が要ります（--points はカンマ区切りで複数可）')
    field = opt('--code-field', 'Code')
    epsg = int(opt('--epsg', DEFAULT_EPSG))
    page_no = int(opt('--page', 0))
    samples = int(opt('--samples', 1))
    outdir = opt('--crop')
    expect = opt('--expect', '4151=1.058,4191=0.773')

    flags = {'--spec', '--calibrate'}
    taken = set()
    for name in ('--pdf', '--points', '--code-field', '--epsg', '--page',
                 '--samples', '--crop', '--expect'):
        if name in args:
            taken.add(args.index(name))
            taken.add(args.index(name) + 1)
    codes = [a for i, a in enumerate(args)
             if i not in taken and not a.startswith('--')]

    dw = Drawing(pdf, page_no=page_no, epsg=epsg)
    points = load_points([p for p in pts.split(',') if p], field)
    if not points:
        die(f'点データに "{field}" 列のコードがありません')

    if '--calibrate' in args:
        pairs = []
        for kv in expect.split(','):
            k, _, v = kv.partition('=')
            pairs.append((k.strip(), float(v)))
        calibrate(dw, points, pairs)
        return
    if not codes:
        die('コードを1つ以上指定してください')
    if outdir:
        crop(dw, points, codes, outdir, samples=samples)
    elif '--spec' in args:
        spec(dw, points, codes, samples=samples)
    else:
        measure(dw, points, codes)


if __name__ == '__main__':
    main()

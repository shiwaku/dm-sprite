# -----------------------------------------
# 図式の記号と、作ったアイコンを並べて見比べるページを作る。
#
#   python3 tools/gen_shape_gallery.py        # _site/shapes.html を書き出す
#
# 左に図式、右にアイコンを置き、tools/verify_shapes.py の判定と数値を添える。
# 数値（比率差・覆い率）は形が合っているかの粗いふるいでしかなく、**最後は目で見て
# 確かめるしかない**。その目視をコード1件ずつ開かずに済ませるためのページ。
#
# 図式は data/zushiki-geometry.json（図式PDFから抜いた記号本体の描画コマンド）から
# SVG に描き起こす。**図式PDFは要らない**。JSON を作り直すときだけ
# tools/dump_zushiki_geometry.py に PDF を渡す。
#
# 大きさは意図的にそろえてある。図式もアイコンもインク外形の長辺を同じ px に
# 正規化して描くので、**このページで比べられるのは形であって大きさではない**
# （設計方針として絶対寸法は図式と違う。docs/icon-authoring-guide.md「3. 大きさを決める」）。
#
# 拡張DMコードは図式に定義が無いので、意匠の根拠は納品図面の実測になる。図面は
# リポジトリに置いていないため、このページでは図式の欄を「図面実測」と出してアイコン
# だけを並べる。
# -----------------------------------------
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '_site', 'shapes.html')

BOX = 64          # 1マスの viewBox
INK = 44          # インク外形の長辺をこの px に正規化する
MIN_STROKE = 0.8  # 図式の線が細すぎて消えないように

# 判定の並び順（気にすべきものを先に）。verify_shapes.py の区分と同じ。
ORDER = ['要確認', '確認済', '判断あり', '字入り', '座標写し', '検証不可', '図式外', '一致']

NOTE = {
    '一致': '比率差10%以下・覆い率85%以上。独立に検証できている',
    '要確認': '数値が基準を外れている。図式側の抽出の問題か、実際のずれかを見分ける',
    '字入り': '○＋文字。字形は書体が違う（Noto Sans JP）ので覆い率は一致しない',
    '座標写し': '図式の座標を写した記号。照合が自己参照になるので独立の根拠にならない',
    '確認済': '数値は外れるが、図式と並べて目視で確認し理由が説明できるもの',
    '判断あり': '図式の一部を除外した（真形の外枠など）。理由は根拠欄',
    '図式外': '図式に点記号の定義が無く、意匠の根拠は納品図面の実測',
    '検証不可': '図式が塗りだけで描かれていて基準形状が取れない',
}


def load_icons():
    path = os.path.join(ROOT, 'data', 'icons.csv')
    with open(path, encoding='utf-8-sig', newline='') as fp:
        return [r for r in csv.DictReader(fp) if r['4桁コード']]


def load_baseline():
    path = os.path.join(ROOT, 'data', 'shape-baseline.csv')
    with open(path, encoding='utf-8-sig', newline='') as fp:
        return {r['コード']: r for r in csv.DictReader(fp)}


def icon_path_data(fname):
    """アイコンSVGのパスデータ。1パスで書く決まりなので最初の d だけ見る。"""
    path = os.path.join(ROOT, 'icons', fname)
    if not os.path.exists(path):
        return None
    m = re.search(r'\sd="([^"]+)"', open(path, encoding='utf-8').read())
    return m.group(1) if m else None


TOKEN = re.compile(r'([MmLlHhVvCcSsQqTtAaZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)')


def path_bbox(d):
    """パスデータのインク外形 (x0, y0, x1, y1)。

    **コマンドを見て座標を取る。** 数値を x,y の並びとみなして拾うと、座標を1つ
    しか取らない H・V が混じったところで x と y が入れ替わる（書体のアウトラインは
    SVGPathPen が H・V を出す）。曲線は制御点で近似する（このページは並べて見せる
    ためのもので、判定は verify_shapes.py が別にやる）。"""
    args = {'M': 2, 'L': 2, 'T': 2, 'S': 4, 'Q': 4, 'C': 6, 'A': 7, 'H': 1, 'V': 1, 'Z': 0}
    toks = [(c, n) for c, n in TOKEN.findall(d)]
    xs, ys, i, cmd = [], [], 0, None
    while i < len(toks):
        c, n = toks[i]
        if c:
            cmd = c.upper()
            i += 1
            if cmd == 'Z':
                continue
        if cmd is None:
            i += 1
            continue
        k = args[cmd]
        vals = []
        while len(vals) < k and i < len(toks) and not toks[i][0]:
            vals.append(float(toks[i][1]))
            i += 1
        if len(vals) < k:
            break
        if cmd == 'H':
            xs.append(vals[0])
        elif cmd == 'V':
            ys.append(vals[0])
        elif cmd == 'A':
            xs.append(vals[5])
            ys.append(vals[6])
        else:
            xs += vals[0::2]
            ys += vals[1::2]
    if not xs or not ys:
        return None
    return min(xs), min(ys), max(xs), max(ys)


def icon_svg(d):
    """アイコンを図式と同じインク寸法（長辺 INK）に正規化した SVG 断片。

    アイコンの絶対寸法は図式と意図的に違うので、そのまま並べると図式の方が
    大きく出て形の違いが見えにくい。ここは形を見比べる場所なので両方そろえる。"""
    bb = path_bbox(d)
    if bb is None:
        return f'<path d="{d}" fill="currentColor"/>'
    x0, y0, x1, y1 = bb
    k = INK / max(x1 - x0, y1 - y0, 1e-6)
    tx = BOX / 2 - (x0 + x1) / 2 * k
    ty = BOX / 2 - (y0 + y1) / 2 * k
    return (f'<g transform="translate({tx:.2f} {ty:.2f}) scale({k:.4f})">'
            f'<path d="{d}" fill="currentColor"/></g>')


def zushiki_svg(items):
    """図式の描画コマンドを 64x64 の SVG 断片にする。

    座標は pt のまま入っているので、インク外形の長辺が INK になるよう拡大して
    中央に置く。線幅も同じ倍率で引き伸ばす（図式の線幅の違い＝大分類の違いが
    見た目に残る）。塗り（fs で塗り色が暗いもの）は塗りつぶす。"""
    pts = [p for it in items for p in it['pts']]
    if not pts:
        return None
    x0 = min(p[0] for p in pts)
    x1 = max(p[0] for p in pts)
    y0 = min(p[1] for p in pts)
    y1 = max(p[1] for p in pts)
    k = INK / max(x1 - x0, y1 - y0, 1e-6)
    ox = BOX / 2 - (x0 + x1) / 2 * k
    oy = BOX / 2 - (y0 + y1) / 2 * k

    def P(p):
        return f'{p[0] * k + ox:.2f} {p[1] * k + oy:.2f}'

    out = []
    for it in items:
        p = it['pts']
        if it['op'] == 'l':
            d = f'M{P(p[0])}L{P(p[1])}'
        elif it['op'] == 'c':
            d = f'M{P(p[0])}C{P(p[1])} {P(p[2])} {P(p[3])}'
        elif it['op'] == 're':
            xa, ya = p[0][0] * k + ox, p[0][1] * k + oy
            xb, yb = p[1][0] * k + ox, p[1][1] * k + oy
            d = (f'M{xa:.2f} {ya:.2f}L{xb:.2f} {ya:.2f}'
                 f'L{xb:.2f} {yb:.2f}L{xa:.2f} {yb:.2f}Z')
        else:
            continue
        w = max(it.get('w', 0.3) * k, MIN_STROKE)
        fill = 'currentColor' if it.get('fill') else 'none'
        out.append(f'<path d="{d}" fill="{fill}" stroke="currentColor" '
                   f'stroke-width="{w:.2f}" stroke-linecap="butt"/>')
    return ''.join(out)


def cell(inner, label):
    """1マス。中身が無いときは理由を書いた枠を出す。

    **プレースホルダも SVG の中に描く。** <svg> の中に HTML の要素を置いても
    表示されない（foreign content になる）ので <text> を使う。"""
    body = inner or (f'<text x="{BOX / 2}" y="{BOX / 2 + 2.5}" text-anchor="middle" '
                     f'font-size="7" fill="currentColor" opacity=".45">{label}</text>')
    return (f'<div class="pane"><svg viewBox="0 0 {BOX} {BOX}" role="img">{body}</svg>'
            f'<span class="cap">{label if inner else "（無し）"}</span></div>')


def card(row, base, geom):
    code, name = row['4桁コード'], row['名称']
    ext = row['分類'] == '拡張DM'
    b = base.get(code, {})
    verdict = b.get('判定') or ('図面実測' if ext else '—')
    entry = geom.get(code) or {}
    zu = zushiki_svg(entry.get('items') or []) if not ext else None
    ic = icon_path_data(row['ファイル名'])
    icon = icon_svg(ic) if ic else None

    nums = ''
    if b.get('比率差'):
        nums = (f'<span title="インク外形の縦横比のずれ">比率差 {b["比率差"]}%</span>'
                f'<span title="アイコンのインクが図式側で覆われる割合。余分な要素に効く">'
                f'ア→図 {b["アイコン→図式"]}%</span>'
                f'<span title="図式のインクがアイコン側で覆われる割合。欠けた要素に効く">'
                f'図→ア {b["図式→アイコン"]}%</span>')
    reason = b.get('根拠') or ''
    if ext:
        reason = f'拡張DM（提供元 {row["提供元"] or "—"}）。意匠の根拠は納品図面の実測'
    return (
        f'<article class="card" data-verdict="{verdict}" '
        f'data-key="{code} {name} {row["ファイル名"]}">'
        f'<header><b>{code}</b> {name}</header>'
        f'<div class="panes">'
        f'{cell(zu, "図式" if not ext else "図面実測")}'
        f'{cell(icon, "アイコン")}'
        f'</div>'
        f'<footer><span class="verdict v-{verdict}">{verdict}</span>'
        f'<span class="nums">{nums}</span>'
        f'{f"<p class=reason>{reason}</p>" if reason else ""}</footer>'
        f'</article>')


CSS = """
:root { --bg:#fff; --fg:#1b1d20; --muted:#6b7280; --line:#e5e7eb; --chip:#f3f4f6; }
* { box-sizing: border-box; }
body { margin:0; padding:24px; background:var(--bg); color:var(--fg);
  font-family: system-ui, "Hiragino Sans", "Noto Sans JP", sans-serif; line-height:1.6; }
h1 { font-size:1.4rem; margin:0 0 4px; }
.lead { color:var(--muted); margin:0 0 16px; max-width:70ch; }
.lead code { background:var(--chip); padding:1px 5px; border-radius:4px; }
.bar { display:flex; flex-wrap:wrap; gap:8px; align-items:center; position:sticky; top:0;
  background:var(--bg); padding:10px 0; border-bottom:1px solid var(--line); z-index:2; }
button { font:inherit; border:1px solid var(--line); background:var(--chip); color:var(--fg);
  border-radius:999px; padding:4px 12px; cursor:pointer; }
button[aria-pressed="true"] { background:var(--fg); color:var(--bg); border-color:var(--fg); }
input { font:inherit; border:1px solid var(--line); border-radius:8px; padding:5px 10px;
  background:var(--bg); color:var(--fg); min-width:14ch; }
.hint { color:var(--muted); font-size:.85rem; }
.grid { display:grid; gap:12px; margin-top:16px;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); }
.card { border:1px solid var(--line); border-radius:10px; padding:10px; }
.card header { font-size:.9rem; margin-bottom:6px; }
.panes { display:flex; gap:8px; }
.pane { flex:1; display:flex; flex-direction:column; align-items:center; gap:2px; }
.pane svg { width:100%; height:auto; aspect-ratio:1; background:var(--chip);
  border-radius:6px; color:var(--fg); }
.cap, .none { font-size:.75rem; color:var(--muted); }
.none { display:flex; align-items:center; justify-content:center; height:100%; }
footer { margin-top:8px; font-size:.78rem; color:var(--muted); }
.nums { display:flex; flex-wrap:wrap; gap:8px; margin-left:8px; }
.verdict { border-radius:999px; padding:1px 8px; background:var(--chip); color:var(--fg); }
.v-要確認 { background:#fde8e8; } .v-一致 { background:#e6f4ea; }
.reason { margin:6px 0 0; }
.section { margin-top:28px; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#14161a; --fg:#e8eaee; --muted:#9aa1ab; --line:#2b2f36; --chip:#1d2026; }
  .v-要確認 { background:#3a2326; } .v-一致 { background:#1f3326; }
}
"""

JS = """
const cards = [...document.querySelectorAll('.card')];
const buttons = [...document.querySelectorAll('.bar button')];
const box = document.querySelector('#q');
let filter = '';
function apply() {
  const q = box.value.trim().toLowerCase();
  let n = 0;
  for (const c of cards) {
    const ok = (!filter || c.dataset.verdict === filter)
      && (!q || c.dataset.key.toLowerCase().includes(q));
    c.hidden = !ok;
    if (ok) n++;
  }
  document.querySelector('#count').textContent = `${n} 件`;
}
for (const b of buttons) {
  b.addEventListener('click', () => {
    filter = b.dataset.verdict === filter ? '' : b.dataset.verdict;
    for (const o of buttons) o.setAttribute('aria-pressed', String(o.dataset.verdict === filter));
    apply();
  });
}
box.addEventListener('input', apply);
apply();
"""


def main():
    icons = load_icons()
    base = load_baseline()
    with open(os.path.join(ROOT, 'data', 'zushiki-geometry.json'), encoding='utf-8') as fp:
        geom = json.load(fp)

    std = [r for r in icons if r['分類'] == '標準図式']
    ext = [r for r in icons if r['分類'] == '拡張DM']
    rank = {v: i for i, v in enumerate(ORDER)}
    std.sort(key=lambda r: (rank.get(base.get(r['4桁コード'], {}).get('判定'), 99),
                            r['4桁コード']))
    ext.sort(key=lambda r: (r['提供元'], r['4桁コード']))

    counts = {}
    for r in std:
        v = base.get(r['4桁コード'], {}).get('判定', '—')
        counts[v] = counts.get(v, 0) + 1

    chips = ''.join(
        f'<button data-verdict="{v}" aria-pressed="false" title="{NOTE.get(v, "")}">'
        f'{v} {counts[v]}</button>'
        for v in ORDER if v in counts)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>図式とアイコンの見比べ — 公共測量成果スプライト</title>
<style>{CSS}</style>
</head>
<body>
<h1>図式とアイコンの見比べ</h1>
<p class="lead">左が<b>図式</b>（作業規程の準則 付録7 の記号本体の描画を
<code>data/zushiki-geometry.json</code> から起こしたもの）、右が<b>このスプライトのアイコン</b>です。
判定と数値は <code>tools/verify_shapes.py</code> のもので、
<code>data/shape-baseline.csv</code> に記録されています。
<br>
<b>大きさは比べられません。</b> どちらもインク外形の長辺をそろえて描いています。
アイコンの絶対寸法は設計方針として図式と意図的に違うためです。</p>

<div class="bar">
  {chips}
  <input id="q" type="search" placeholder="コード・名称で絞る">
  <span class="hint" id="count"></span>
</div>

<div class="grid">
{''.join(card(r, base, geom) for r in std)}
</div>

<div class="section">
<h1>拡張DMコード</h1>
<p class="lead">標準図式に定義が無いコードです。意匠の根拠は納品図面の実測で、図面は
リポジトリに置いていないため図式の欄は空です。キーには提供元の区画が入ります
（<code>dm-toyonaka-4133</code>）。</p>
<div class="grid">
{''.join(card(r, base, geom) for r in ext)}
</div>
</div>

<script>{JS}</script>
</body>
</html>
"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fp:
        fp.write(html)
    miss = [r['4桁コード'] for r in std if not (geom.get(r['4桁コード']) or {}).get('items')]
    print(f'{OUT} を生成しました（標準図式 {len(std)}件 / 拡張DM {len(ext)}件）')
    print(f'  図式の描画が取れないコード {len(miss)}件: {" ".join(miss)}')


if __name__ == '__main__':
    main()

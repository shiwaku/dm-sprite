# -----------------------------------------
# 公共測量標準図式 PDF の「数値地形図データ取得分類基準表」から
# 分類コード・名称・データタイプを抽出して data/symbols.csv を書き出す。
#
#   python3 tools/extract_symbol_table.py <図式PDFのパス>
#
# PDF は国土地理院が公開している「作業規程の準則 付録7 公共測量標準図式」。
#   https://www.gsi.go.jp/common/000258741.pdf
# リポジトリには同梱しない（8MB あり、一次資料は配布元から取るのが筋なので）。
#
# 抽出対象は横向きページの取得分類基準表3種:
#   標準図式（レイヤ11〜81） / 応用測量（線形図・用地・整飾） / 測量記録
# 縦向きの注記ページは全件 E7（注記）で点記号を含まないため対象外。
#
# 表の読み方は PDF の「図式の見方」ページのとおり。列位置はページごとに
# 微妙に違う（応用測量の表は本体より右にずれている）ので、罫線と見出し文字
# から列を割り出している。
# -----------------------------------------
import csv
import os
import re
import sys
from collections import defaultdict

import fitz  # PyMuPDF

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'symbols.csv')
OVERRIDES = os.path.join(ROOT, 'data', 'symbols-overrides.csv')

PDF_URL = 'https://www.gsi.go.jp/common/000258741.pdf'

# レコードタイプ欄に入る値（図式の見方より）。E1面 E2線 E3円 E4円弧 E5点
# E6方向 E7注記 E8属性 G グリッド T 不整三角網。日本語のデータタイプ欄と
# レコードタイプ欄が「方向E6」のようにひとつの語として抽出されるページが
# あるので、語の中から拾う。
RECORD_TYPE = re.compile(r'E[1-8]')
GRID_TYPES = (('グリッド', 'G'), ('不整三角網', 'T'))
POINT_TYPES = ('E5', 'E6')  # 点・方向。アイコンが要るのはこの2つ

# セクションの切り替わりは「附属資料」の中扉で判断する
SECTION_MARKS = (
    ('取得分類基準表　応用測量', '応用測量'),
    ('取得分類基準表　測量記録', '測量記録'),
)
# 取得分類コード表以降は基準表ではないので打ち切る
SECTION_END = '取得分類コード表'


def horizontal_segments(page):
    """横罫線を (y, x0, x1) で返す。図式欄の記号見本の線も混ざる。"""
    segs = []
    for grp in page.get_drawings():
        for item in grp['items']:
            if item[0] == 'l':
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 0.6 and abs(p1.x - p2.x) > 3:
                    segs.append((round(p1.y, 1), min(p1.x, p2.x), max(p1.x, p2.x)))
            elif item[0] == 're':
                r = item[1]
                if r.height < 0.8 and r.width > 3:
                    segs.append((round(r.y0, 1), r.x0, r.x1))
    return segs


def full_width_rules(segs):
    """表を横断する罫線の (y, x0) を返す。y 昇順。列を割り出すための足場。"""
    right = max((x1 for _, _, x1 in segs), default=0.0)
    best = {}
    for y, x0, x1 in segs:
        if x1 > right - 2 and (y not in best or x0 < best[y]):
            best[y] = round(x0, 1)
    return sorted(best.items())


def row_rules(segs, item_col, layer_col, top, bottom):
    """行の切れ目 (y, レイヤも切れているか) を返す。

    適用欄や備考欄が縦に結合している行では罫線が右端まで届かないので、
    「データ項目の列を横切っているか」で行の切れ目を判定する。さらに
    レイヤ列まで横切っていればレイヤ（結合セル）の切れ目でもある。"""
    breaks = {}
    for y, x0, x1 in segs:
        if not (top - 1 <= y <= bottom + 1):
            continue
        if x0 <= item_col[0] + 1 and x1 >= item_col[1] - 1:
            new_layer = x0 <= layer_col[0] + 1
            breaks[y] = breaks.get(y, False) or new_layer
    return sorted(breaks.items())


def full_height_columns(page, header_bottom, bottom):
    """表の高さを縦断する罫線の x を返す。列の境界になる。

    見出しが「分類コード」→「レイヤ／データ項目」のように結合している列が
    あるので、上端は見出しの下辺まで届いていればよいとする。逆に下端は表の
    最下辺まで要る（地図情報レベルの 500/1000/… は見出し内だけの区切りなので
    これで落ちる）。

    罫線は見出し部と本体部で別のセグメントに分かれて描かれているページが
    あるので、同じ x のセグメントはつないでから判定する。"""
    xs = []
    for grp in page.get_drawings():
        for item in grp['items']:
            if item[0] == 'l':
                p1, p2 = item[1], item[2]
                if abs(p1.x - p2.x) < 0.6 and abs(p1.y - p2.y) > 3:
                    xs.append((p1.x, min(p1.y, p2.y), max(p1.y, p2.y)))
            elif item[0] == 're':
                r = item[1]
                if r.width < 0.8 and r.height > 3:
                    xs.append((r.x0, r.y0, r.y1))
    merged = {}
    for x, y0, y1 in xs:
        x = round(x, 1)
        lo, hi = merged.get(x, (y0, y1))
        merged[x] = (min(lo, y0), max(hi, y1))
    return sorted(x for x, (y0, y1) in merged.items()
                  if y0 < header_bottom - 2 and y1 > bottom - 5)


def column_label(words, x0, x1, top, bottom):
    """列の見出し文字を読む。縦書きなので x でまとめて y 順に連ねる。"""
    cols = defaultdict(list)
    for x, y, _, _, t, *_ in words:
        if x0 - 0.5 <= x < x1 and top <= y < bottom:
            cols[round(x, 0)].append((y, t))
    parts = []
    for x in sorted(cols):
        parts.append(''.join(t for _, t in sorted(cols[x])))
    return re.sub(r'\s|　', '', ''.join(parts))


def header_band(words, rules):
    """見出し行の (上辺, 下辺) を返す。

    見出しの上辺に罫線が無いページがあるので、横書きで入っている「取得方法」
    の位置を頼りに、その上下の罫線で挟む。"""
    ys = [y for x, y, _, _, t, *_ in words if t == '取得方法']
    if not ys:
        return None
    y = min(ys)
    above = [r for r, _ in rules if r < y]
    below = [r for r, _ in rules if r > y]
    if not below:
        return None
    return (max(above) if above else 0.0), min(below)


def find_columns(page, words, rules, header):
    """(レイヤ列, データ項目列, 名称列, 取得方法列, データタイプ列) の x 範囲を返す。"""
    header_top, header_bottom = header
    xs = full_height_columns(page, header_bottom, rules[-1][0])
    if len(xs) < 5:
        return None
    spans = {}
    for x0, x1 in zip(xs, xs[1:]):
        label = column_label(words, x0, x1, header_top, header_bottom)
        spans[(x0, x1)] = label

    layer = item = name = method = dtype = record = None
    for (x0, x1), label in spans.items():
        if 'レイヤ' in label:
            layer = (x0, x1)
        elif '項目' in label and 'データ' in label:
            item = (x0, x1)
        elif '名称' in label:
            name = (x0, x1)
        elif '取得方法' in label:
            method = (x0, x1)
        elif sorted(label) == sorted('データ'):  # 縦書きの読み順が揺れる
            dtype = (x0, x1)
        elif sorted(label) == sorted('レコード'):
            record = (x0, x1)
    if not (layer and item and name and dtype and record):
        return None
    # データタイプ欄とレコードタイプ欄はまとめて読む（語が結合しているため）
    return layer, item, name, method, (dtype[0], record[1])


def text_in(words, span, y0, y1):
    """列 span・行 y0〜y1 に入る文字を読み順に連ねる。"""
    if span is None:
        return ''
    x0, x1 = span
    got = [(round(y, 1), x, t) for x, y, _, _, t, *_ in words
           if x0 - 0.5 <= x < x1 and y0 <= y < y1]
    return ''.join(t for _, _, t in sorted(got))


def clean(s):
    return re.sub(r'\s+', '', s.replace('　', '')).strip()


def parse_page(page, pageno, section, major, rows, state):
    words = page.get_text('words')
    segs = horizontal_segments(page)
    rules = full_width_rules(segs)
    if len(rules) < 2:
        return
    header = header_band(words, rules)
    if header is None:
        return
    cols = find_columns(page, words, rules, header)
    if cols is None:
        return
    layer_col, item_col, name_col, method_col, type_col = cols

    header_bottom, bottom = header[1], rules[-1][0]
    breaks = row_rules(segs, item_col, layer_col, header_bottom, bottom)
    if len(breaks) < 2:
        return

    for (y0, new_layer), (y1, _) in zip(breaks, breaks[1:]):
        if y1 <= y0:
            continue
        if new_layer:
            # 新しいレイヤブロック。結合セルの数字を読む
            got = clean(text_in(words, layer_col, y0, bottom + 0.1))
            m = re.search(r'\d{2}', got)
            if m:
                state['layer'] = m.group(0)

        item = clean(text_in(words, item_col, y0, y1))
        name = clean(text_in(words, name_col, y0, y1))
        method = clean(text_in(words, method_col, y0, y1))
        type_text = text_in(words, type_col, y0, y1)
        types = set(RECORD_TYPE.findall(type_text))
        types |= {code for word, code in GRID_TYPES if word in type_text}
        types = sorted(types, key=lambda t: (t[0], t))

        if re.fullmatch(r'[―－\-‐]+', item):
            # 分類コードを持たない図式（ダム等）。台帳には載せない
            continue
        m = re.fullmatch(r'\d{2}', item)
        if not m:
            # 行が続いている（ページ跨ぎ・名称の折り返し）ので直前の行に足す
            if rows and (name or types):
                prev = rows[-1]
                prev['名称'] += name
                prev['取得方法'] = (prev['取得方法'] + method).strip()
                prev['データタイプ'] = sorted(set(prev['データタイプ']) | set(types),
                                        key=lambda t: (t[0], t))
            continue
        if not state.get('layer'):
            continue

        code = state['layer'] + item
        if rows and rows[-1]['コード'] == code and rows[-1]['図式区分'] == section:
            # ページを跨いだ続き。同じコードの行が改めて立っている
            prev = rows[-1]
            prev['名称'] += name
            prev['取得方法'] += method
            prev['データタイプ'] = sorted(set(prev['データタイプ']) | set(types),
                                    key=lambda t: (t[0], t))
            continue

        rows.append({
            '図式区分': section,
            'コード': code,
            '大分類': major,
            '名称': name,
            'データタイプ': types,
            '取得方法': method,
            'PDFページ': pageno,
        })


def extract(pdf_path):
    doc = fitz.open(pdf_path)
    rows = []
    state = {'layer': None}
    section = None
    started = False
    for i in range(doc.page_count):
        page = doc[i]
        text = page.get_text()
        head = clean(text.split('\n')[0]) if text.strip() else ''

        if '図式の見方' in text[:200]:
            started, section = True, '標準図式'
            continue
        if not started:
            continue
        if SECTION_END in text[:200]:
            break
        for mark, label in SECTION_MARKS:
            if mark in text[:200]:
                section, state['layer'] = label, None
        if page.rect.width < page.rect.height:
            continue  # 縦向きの注記ページ
        parse_page(page, i + 1, section, head, rows, state)
    return rows


def load_icons():
    """4桁コード -> アイコンファイル名。ここでは進捗の表示にだけ使う。

    どのコードにアイコンがあるかは icons.csv 側の情報なので、台帳には焼き込まず
    docs/symbol-coverage.md の生成時に突き合わせる（そうしないとアイコンを足す
    たびに図式PDFから再抽出しないと数字が動かない）。"""
    icons = defaultdict(list)
    path = os.path.join(ROOT, 'data', 'icons.csv')
    with open(path, encoding='utf-8-sig', newline='') as fp:
        for row in csv.DictReader(fp):
            code = row['4桁コード'].strip()
            if code:
                icons[code].append(row['ファイル名'])
    return icons


def load_overrides():
    """図式のデータタイプだけではアイコンの要否を判定できないコードの上書き。

    #6 のコメントのとおり、図式で面（E1）としか定義されていないコードでも
    実データでは方向（E6）で入っていることがある（2235 雨水桝）。図式だけを
    根拠にすると「面なのでアイコン不要」と誤判定するので、第2の根拠を持たせる。"""
    if not os.path.exists(OVERRIDES):
        return {}
    out = {}
    with open(OVERRIDES, encoding='utf-8-sig', newline='') as fp:
        for row in csv.DictReader(fp):
            out[row['コード'].strip()] = row
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(f'使い方: python3 tools/extract_symbol_table.py <図式PDF>\n'
                 f'  PDF: {PDF_URL}')
    pdf = sys.argv[1]
    if not os.path.exists(pdf):
        sys.exit(f'PDF が見つかりません: {pdf}\n  取得元: {PDF_URL}')

    rows = extract(pdf)
    icons = load_icons()
    overrides = load_overrides()

    dupes = defaultdict(int)
    for r in rows:
        dupes[(r['図式区分'], r['コード'])] += 1

    out_rows = []
    for r in rows:
        code = r['コード']
        types = r['データタイプ']
        target = any(t in POINT_TYPES for t in types)
        ov = overrides.get(code)
        reason = ''
        if target:
            reason = '図式'
        elif ov:
            target, reason = True, ov['根拠']
        out_rows.append({
            '図式区分': r['図式区分'],
            '大分類': r['大分類'],
            'コード': code,
            '名称': r['名称'],
            'データタイプ': '/'.join(types),
            'アイコン対象': '○' if target else '',
            '対象の根拠': reason,
            '取得方法': r['取得方法'],
            'PDFページ': r['PDFページ'],
        })

    out_rows.sort(key=lambda r: (r['図式区分'] != '標準図式', r['コード']))
    with open(OUT, 'w', encoding='utf-8', newline='') as fp:
        w = csv.DictWriter(fp, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)

    print(f'{OUT} を書き出しました（{len(out_rows)}件）')
    for section in ('標準図式', '応用測量', '測量記録'):
        rs = [r for r in out_rows if r['図式区分'] == section]
        target = [r for r in rs if r['アイコン対象']]
        done = [r for r in target if icons.get(r['コード'])]
        print(f'  {section}: {len(rs)}コード / アイコン対象 {len(target)}件 / '
              f'作成済み {len(done)}件 / 未作成 {len(target) - len(done)}件')
    bad = [k for k, v in dupes.items() if v > 1]
    if bad:
        print(f'  同じコードが複数行にわたっています: {bad}', file=sys.stderr)


if __name__ == '__main__':
    main()

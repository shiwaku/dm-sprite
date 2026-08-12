# -----------------------------------------
# data/symbols.csv から docs/symbol-coverage.md を生成する。
#
#   python3 tools/gen_symbol_coverage.py
#
# 台帳そのものは tools/extract_symbol_table.py が図式PDFから作る。
# この生成には PDF は要らない（台帳とアイコンの突き合わせだけ）。
# -----------------------------------------
import csv
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYMBOLS = os.path.join(ROOT, 'data', 'symbols.csv')
OVERRIDES = os.path.join(ROOT, 'data', 'symbols-overrides.csv')
OUT = os.path.join(ROOT, 'docs', 'symbol-coverage.md')

SECTIONS = ('標準図式', '応用測量', '測量記録')
SECTION_NOTE = {
    '標準図式': '地図情報レベル500〜5000。都市計画基本図・道路台帳平面図などが従う本体の図式',
    '応用測量': '線形図・用地・整飾。分類基準表（本体）には載らない別系統',
    '測量記録': '基準点網図・水準路線図・数値写真資料。測量の記録用',
}


def load(path, key=None):
    with open(path, encoding='utf-8-sig', newline='') as fp:
        rows = list(csv.DictReader(fp))
    return {r[key]: r for r in rows} if key else rows


def bar(done, total, width=20):
    if not total:
        return ''
    n = round(width * done / total)
    return '█' * n + '░' * (width - n)


def main():
    rows = load(SYMBOLS)
    overrides = load(OVERRIDES, 'コード') if os.path.exists(OVERRIDES) else {}

    lines = [
        '# 点記号カバレッジ',
        '',
        '> `python3 tools/gen_symbol_coverage.py` で生成。直接編集しない。',
        '',
        '公共測量標準図式に定義された記号のうち、点アイコンが要るものが何件で、',
        'そのうち何件を `icons/` に持っているかの一覧。台帳は',
        '[`data/symbols.csv`](../data/symbols.csv)で、',
        '[作業規程の準則 付録7 公共測量標準図式](https://www.gsi.go.jp/common/000258741.pdf)の',
        '「数値地形図データ取得分類基準表」から `tools/extract_symbol_table.py` で抽出している。',
        '',
        'アイコン対象の判定は、図式のデータタイプが**点（E5）または方向（E6）**であること。',
        'ただし図式が面・線でも実データが点で入るコードがあるため、',
        '[`data/symbols-overrides.csv`](../data/symbols-overrides.csv)で個別に対象へ足している。',
        '',
        '## 全体',
        '',
        '| 図式区分 | コード数 | アイコン対象 | 作成済み | 未作成 | 進捗 |',
        '|---|---:|---:|---:|---:|---|',
    ]

    total_t = total_d = 0
    for section in SECTIONS:
        rs = [r for r in rows if r['図式区分'] == section]
        target = [r for r in rs if r['アイコン対象']]
        done = [r for r in target if r['アイコン']]
        total_t += len(target)
        total_d += len(done)
        pct = f'{len(done) / len(target) * 100:.0f}%' if target else '—'
        lines.append(f'| {section} | {len(rs)} | {len(target)} | {len(done)} | '
                     f'{len(target) - len(done)} | `{bar(len(done), len(target))}` {pct} |')
    lines.append(f'| **合計** | **{len(rows)}** | **{total_t}** | **{total_d}** | '
                 f'**{total_t - total_d}** | `{bar(total_d, total_t)}` '
                 f'**{total_d / total_t * 100:.0f}%** |')

    lines += ['']
    for section in SECTIONS:
        lines.append(f'- **{section}** — {SECTION_NOTE[section]}')
    lines += ['']

    # 標準図式の大分類別
    std = [r for r in rows if r['図式区分'] == '標準図式']
    lines += [
        '## 標準図式の大分類別',
        '',
        '| 大分類 | コード数 | アイコン対象 | 作成済み | 未作成 |',
        '|---|---:|---:|---:|---:|',
    ]
    order = []
    for r in std:
        if r['大分類'] not in order:
            order.append(r['大分類'])
    for major in order:
        rs = [r for r in std if r['大分類'] == major]
        target = [r for r in rs if r['アイコン対象']]
        done = [r for r in target if r['アイコン']]
        lines.append(f'| {major} | {len(rs)} | {len(target)} | {len(done)} | '
                     f'{len(target) - len(done)} |')

    # 未作成一覧
    todo = [r for r in rows if r['アイコン対象'] and not r['アイコン']]
    lines += ['', f'## 未作成 {len(todo)}件', '']
    groups = defaultdict(list)
    for r in todo:
        groups[(r['図式区分'], r['大分類'])].append(r)
    for section in SECTIONS:
        keys = [k for k in groups if k[0] == section]
        if not keys:
            continue
        for key in keys:
            items = sorted(groups[key], key=lambda r: r['コード'])
            head = key[1] if section == '標準図式' else f'{section} / {key[1]}'
            lines += [
                f'### {head}（{len(items)}件）',
                '',
                '| コード | 名称 | データタイプ | 対象の根拠 | 図式PDF |',
                '|---|---|---|---|---:|',
            ]
            for r in items:
                lines.append(f"| {r['コード']} | {r['名称']} | {r['データタイプ'] or '—'} | "
                             f"{r['対象の根拠']} | p{r['PDFページ']} |")
            lines.append('')

    # 図式以外を根拠にしたもの
    special = [r for r in rows if r['対象の根拠'] and r['対象の根拠'] != '図式']
    if special:
        lines += [
            '## 図式のデータタイプ以外を根拠に対象へ入れたコード',
            '',
            '| コード | 名称 | データタイプ | 根拠 | 理由 |',
            '|---|---|---|---|---|',
        ]
        for r in sorted(special, key=lambda r: r['コード']):
            ov = overrides.get(r['コード'], {})
            lines.append(f"| {r['コード']} | {r['名称']} | {r['データタイプ']} | "
                         f"{r['対象の根拠']} | {ov.get('理由', '')} |")
        lines.append('')

    # 対象外だがアイコンを持っているコードの検算用
    orphan = [r for r in rows if r['アイコン'] and not r['アイコン対象']]
    if orphan:
        lines += ['## アイコンはあるが対象外のコード', '']
        for r in orphan:
            lines.append(f"- {r['コード']} {r['名称']}（{r['データタイプ']}）")
        lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fp:
        fp.write('\n'.join(lines))
    print(f'{OUT} を生成しました（対象 {total_t}件 / 作成済み {total_d}件 / '
          f'未作成 {total_t - total_d}件）')

    # icons.csv 側に台帳と食い違うコードが無いかの検算
    icons = load(os.path.join(ROOT, 'data', 'icons.csv'))
    known = {r['コード'] for r in rows}
    unknown = sorted({r['4桁コード'] for r in icons
                      if r['分類'] == '標準図式' and r['4桁コード'] not in known})
    if unknown:
        print(f'  標準図式とされているが台帳に無いコード: {" ".join(unknown)}')
    print('  大分類別コード数:', dict(Counter(r['大分類'] for r in std)))


if __name__ == '__main__':
    main()

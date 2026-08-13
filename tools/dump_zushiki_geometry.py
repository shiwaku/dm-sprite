# -----------------------------------------
# 図式PDFから記号本体の描画要素を抜き、data/zushiki-geometry.json に書き出す。
#
#   python3 tools/dump_zushiki_geometry.py <図式PDF>
#
# アイコンが図式の形と一致しているかの判定（tools/verify_shapes.py）は、この
# JSON を基準に行う。**PDF は基準を作り直すときだけ必要**で、日々の判定と CI では
# JSON だけを使う。
#
# 抽出の内容:
#   図式欄（列見出しが「図式」の列）の、記号本体の線幅を持つ描画だけ。
#   線幅は大分類ごとに違う（建物等0.6・小物体0.45・土地利用等0.3・42-55だけ0.9）。
#   寸法の引出線は0.15pt、矢印と数字は幅を持たない塗りなので、0.3pt 以上という
#   条件で本体だけが残る。縦に並ぶ変種のうち、いちばん上（レベル500/1000用）を採る。
#
# **この JSON は目視でレビューしたうえでコミットする。** 抽出が間違っていれば
# 判定も一緒に間違うため、ここがレビューの対象。除外した要素は EXCLUDE に理由つきで
# 記録する（真形の外枠・寸法の補助線など）。
# -----------------------------------------
import json
import os
import sys

import fitz

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_shapes as V  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'zushiki-geometry.json')


def main():
    if len(sys.argv) < 2:
        sys.exit(f'使い方: python3 tools/dump_zushiki_geometry.py <図式PDF>\n'
                 f'  PDF: {V.PDF_URL}')
    pdf = sys.argv[1]
    if not os.path.exists(pdf):
        sys.exit(f'PDF が見つかりません: {pdf}\n  取得元: {V.PDF_URL}')

    codes = {code for code, _ in V.targets(set())}
    doc = fitz.open(pdf)
    cells = V.find_cells(doc, codes)

    out = {}
    for code in sorted(codes):
        cell = cells.get(code)
        if cell is None:
            continue
        items = V.body_items(doc, cell, code)
        if not items:
            out[code] = dict(name=cell['name'], page=cell['page'] + 1, items=[],
                             note='本体の描画が取れない（塗りだけで描かれた記号）')
            continue
        out[code] = dict(
            name=cell['name'], page=cell['page'] + 1,
            excluded=code in V.EXCLUDE,
            items=[dict(op=it[0], w=it[1], pts=it[2], fill=bool(it[3]) if len(it) > 3 else False)
                   for it in items])

    with open(OUT, 'w', encoding='utf-8') as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1, sort_keys=True)
    got = [c for c, v in out.items() if v['items']]
    print(f'{OUT} を書き出しました（{len(out)}コード / 形状が取れた {len(got)}件 / '
          f'取れない {len(out) - len(got)}件）')
    if len(out) != len(got):
        print('  取れない:', ' '.join(c for c, v in out.items() if not v['items']))


if __name__ == '__main__':
    main()

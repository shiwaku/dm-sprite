# -----------------------------------------
# icons/ の内容と git 履歴から docs/icon-list.md を生成する。
#
#   python3 tools/gen_icon_list.py
#
# 名称は data/icons.csv（ファイル名,4桁コード,名称,分類）から引く。
# アイコンを追加したら data/icons.csv に行を足してから実行する。
# 追加日は git log --diff-filter=A から取るので、コミット後に実行すること。
# -----------------------------------------
import csv
import os
import subprocess
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'docs', 'icon-list.md')


def git(*args):
    return subprocess.run(('git',) + args, cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def load_names():
    path = os.path.join(ROOT, 'data', 'icons.csv')
    names = {}
    with open(path, encoding='utf-8-sig', newline='') as fp:
        for row in csv.DictReader(fp):
            names[row['ファイル名']] = (row['名称'], row['分類'])
    return names


def added_info(fname):
    """そのファイルが追加されたコミットの日付・ハッシュ・件名を返す。
    改名（0296aa9 でアイコンを一斉リネームしている）を辿るため --follow を使うが、
    既定の類似度判定だと無関係なアイコンからの改名と誤検出して追加日がずれるので、
    -M100%（内容が完全一致する改名だけを辿る）を付ける。"""
    out = git('log', '--diff-filter=A', '--follow', '-M100%', '--date=short',
              '--format=%ad\t%h\t%s', '-1', '--', f'icons/{fname}')
    if not out:
        return ('-', '-', '')
    return tuple(out.split('\t', 2))


def main():
    names = load_names()
    files = sorted(f for f in os.listdir(os.path.join(ROOT, 'icons'))
                   if f.endswith('.svg'))

    rows = []
    missing = []
    for f in files:
        name, kind = names.get(f, ('', '—'))
        if f not in names:
            missing.append(f)
        date, sha, subject = added_info(f)
        rows.append((f, name, kind, date, sha, subject))

    batches = defaultdict(list)
    for r in rows:
        batches[(r[3], r[4], r[5])].append(r)

    lines = [
        '# アイコン一覧',
        '',
        '> `python3 tools/gen_icon_list.py` で生成。直接編集しない。',
        '',
        f'収録数: **{len(files)}件**',
        '',
        '## 追加履歴',
        '',
        '| 追加日 | 件数 | コミット | 内容 | コード |',
        '|---|---:|---|---|---|',
    ]
    for (date, sha, subject), items in sorted(batches.items(), reverse=True):
        codes = ' '.join(i[0].removeprefix('dm-').removesuffix('.svg') for i in items)
        if len(codes) > 120:
            codes = codes[:117] + '…'
        lines.append(f'| {date} | {len(items)} | `{sha}` | {subject} | {codes} |')

    lines += [
        '',
        '## 一覧',
        '',
        '| | ファイル | コード | 名称 | 分類 | 追加日 |',
        '|---|---|---|---|---|---|',
    ]
    for f, name, kind, date, sha, _ in rows:
        img = f'<img src="../icons/{f}" width="28" height="28">'
        code = f.removeprefix('dm-').removesuffix('.svg') if f.startswith('dm-') else '—'
        lines.append(f'| {img} | `{f}` | {code} | {name} | {kind} | {date} |')

    lines.append('')
    with open(OUT, 'w', encoding='utf-8') as fp:
        fp.write('\n'.join(lines))

    write_readme_history(batches, names, len(files))

    print(f'{OUT} を生成しました（{len(files)}件）')
    if missing:
        print(f'  data/icons.csv に未登録: {" ".join(missing)}', file=sys.stderr)


BEGIN = '<!-- icon-history:start -->'
END = '<!-- icon-history:end -->'


def write_readme_history(batches, names, total):
    """README のマーカー間に更新履歴を差し込む。"""
    path = os.path.join(ROOT, 'README.md')
    s = open(path, encoding='utf-8').read()
    if BEGIN not in s or END not in s:
        print(f'  README.md に {BEGIN} / {END} が無いため履歴は差し込みませんでした',
              file=sys.stderr)
        return

    body = [f'収録数 **{total}件**。日付は git 履歴（そのファイルが追加されたコミット）による。',
            '',
            '| 追加日 | 件数 | 追加したアイコン | 内容 |',
            '|---|---:|---|---|']
    for (date, sha, subject), items in sorted(batches.items(), reverse=True):
        thumbs = ' '.join(
            f'<img src="icons/{i[0]}" width="22" height="22" title="{i[1] or i[0]}">'
            for i in items)
        body.append(f'| {date} | {len(items)} | {thumbs} | {subject} |')
    body += ['', 'コードと名称は [docs/icon-list.md](docs/icon-list.md) を参照。']

    head, rest = s.split(BEGIN, 1)
    _, tail = rest.split(END, 1)
    open(path, 'w', encoding='utf-8').write(
        head + BEGIN + '\n\n' + '\n'.join(body) + '\n\n' + END + tail)
    print('README.md の更新履歴を差し込みました')


if __name__ == '__main__':
    main()

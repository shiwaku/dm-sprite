# Smart City 公共測量成果Sprite

公共測量標準図式（作業規程の準則 付録7）の地図記号を、MapLibre 向けスプライトシートとして配信する。

## アイコンを追加する

| ドキュメント | 内容 |
|---|---|
| [docs/icon-authoring-guide.md](docs/icon-authoring-guide.md) | 標準図式から SVG を起こす手順（図式の読み取り・大きさの決め方・作図・検証・公開） |
| [docs/svg-design-spec.md](docs/svg-design-spec.md) | SVG 設計基準（64×64・単色・ストローク不使用など） |

作図と検証には `tools/` のスクリプトを使う。

```bash
python3 tools/gen_icons.py --install   # 作図ヘルパと作例。icons/ に書き出す
python3 tools/inspect_icons.py dm-7212 # bbox・中心・線幅を実測
```

---

## ビルドと公開

```bash
npm install
npm run build   # _site/ に sprite.png / sprite.json / sprite@2x.png / sprite@2x.json の4ファイルを生成
npm run start   # ビルドしてローカルサーバーを起動（http://localhost:8080）
```

`main` に push すると GitHub Actions がビルドして GitHub Pages にデプロイする。
公開先は `https://<GitHub username>.github.io/<repository name>/sprite.png` など上記4ファイル。

MapLibre に複数のスプライトシートを読み込ませる方法は [公式ドキュメント](https://maplibre.org/maplibre-style-spec/sprite/#multiple-sprite-sources) を参照。

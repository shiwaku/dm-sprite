# 公共測量成果スプライト

公共測量標準図式（作業規程の準則 付録7）の地図記号を、MapLibre 向けスプライトシートとして配信する。

## アイコンを追加する

| ドキュメント | 内容 |
|---|---|
| [docs/icon-list.md](docs/icon-list.md) | 収録アイコンの一覧と追加履歴 |
| [docs/icon-authoring-guide.md](docs/icon-authoring-guide.md) | 標準図式から SVG を起こす手順（図式の読み取り・大きさの決め方・作図・検証・公開） |
| [docs/svg-design-spec.md](docs/svg-design-spec.md) | SVG 設計基準（64×64・単色・ストローク不使用など） |

作図と検証には `tools/` のスクリプトを使う。

```bash
python3 tools/gen_icons.py --install   # 作図ヘルパと作例。icons/ に書き出す
python3 tools/inspect_icons.py dm-7212 # bbox・中心・線幅を実測
python3 tools/gen_icon_list.py         # docs/icon-list.md を再生成
```

アイコンを追加したら [`data/icons.csv`](data/icons.csv)（名称のマスタ）に行を足し、コミット後に `gen_icon_list.py` を実行して一覧を更新する。

---

## 更新履歴

<!-- icon-history:start -->

収録数 **113件**。日付は git 履歴（そのファイルが追加されたコミット）による。

| 追加日 | 件数 | 追加したアイコン | 内容 |
|---|---:|---|---|
| 2026-08-11 | 6 | <img src="icons/dm-2219.svg" width="22" height="22" title="道路のトンネル"> <img src="icons/dm-3519.svg" width="22" height="22" title="役場支所及び出張所"> <img src="icons/dm-3531.svg" width="22" height="22" title="保健所"> <img src="icons/dm-5227.svg" width="22" height="22" title="せき"> <img src="icons/dm-6335.svg" width="22" height="22" title="はい松地"> <img src="icons/dm-7212.svg" width="22" height="22" title="露岩"> | 不足していた標準図式アイコン6件を追加 |
| 2026-02-26 | 8 | <img src="icons/dm-4239.svg" width="22" height="22" title="風車"> <img src="icons/dm-5221.svg" width="22" height="22" title="渡船発着所"> <img src="icons/dm-6314.svg" width="22" height="22" title="さとうきび畑"> <img src="icons/dm-6337.svg" width="22" height="22" title="やし科樹林"> <img src="icons/dm-7206.svg" width="22" height="22" title="洞口"> <img src="icons/dm-7303.svg" width="22" height="22" title="多角点等"> <img src="icons/dm-7304.svg" width="22" height="22" title="公共基準点（三角点）"> <img src="icons/dm-7305.svg" width="22" height="22" title="公共基準点（水準点）"> | 不足アイコンを追加 |
| 2026-02-20 | 8 | <img src="icons/dm-2242.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-2243.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-2244.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-2245.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-9101100.svg" width="22" height="22" title="起終点_道路（起点）"> <img src="icons/dm-9101200.svg" width="22" height="22" title="起終点_道路（終点）"> <img src="icons/dm-9109.svg" width="22" height="22" title="官民境界杭_道路"> <img src="icons/dm-9303220.svg" width="22" height="22" title="警報遮断機_道路"> | add road  icons |
| 2026-02-10 | 18 | <img src="icons/dm-3515.svg" width="22" height="22" title="交番・駐在所"> <img src="icons/dm-3530.svg" width="22" height="22" title="老人ホーム"> <img src="icons/dm-3546.svg" width="22" height="22" title="火薬庫"> <img src="icons/dm-3560.svg" width="22" height="22" title="ガソリンスタンド"> <img src="icons/dm-4221.svg" width="22" height="22" title="独立樹（広葉樹）"> <img src="icons/dm-4222.svg" width="22" height="22" title="独立樹（針葉樹）"> <img src="icons/dm-4231.svg" width="22" height="22" title="タンク"> <img src="icons/dm-4241.svg" width="22" height="22" title="灯台"> <img src="icons/dm-4243.svg" width="22" height="22" title="灯標"> <img src="icons/dm-4251.svg" width="22" height="22" title="水位観測所"> <img src="icons/dm-5232.svg" width="22" height="22" title="透過水制"> <img src="icons/dm-6212.svg" width="22" height="22" title="駐車場"> <img src="icons/dm-6217.svg" width="22" height="22" title="太陽光発電設備"> <img src="icons/dm-6222.svg" width="22" height="22" title="温泉・鉱泉"> <img src="icons/dm-6318.svg" width="22" height="22" title="茶畑"> <img src="icons/dm-7201.svg" width="22" height="22" title="土がけ"> <img src="icons/dm-7211.svg" width="22" height="22" title="岩がけ"> <img src="icons/dm-7311.svg" width="22" height="22" title="標石を有しない標高点"> | add dm icons |
| 2026-01-30 | 14 | <img src="icons/dm-2238.svg" width="22" height="22" title="並木"> <img src="icons/dm-2239.svg" width="22" height="22" title="植樹"> <img src="icons/dm-2253.svg" width="22" height="22" title="カーブミラー"> <img src="icons/dm-4101.svg" width="22" height="22" title="マンホール（未分類）"> <img src="icons/dm-4111.svg" width="22" height="22" title="マンホール（共同溝）"> <img src="icons/dm-4121.svg" width="22" height="22" title="マンホール（ガス）"> <img src="icons/dm-4131.svg" width="22" height="22" title="マンホール（電話）"> <img src="icons/dm-4141.svg" width="22" height="22" title="マンホール（電気）"> <img src="icons/dm-4151.svg" width="22" height="22" title="マンホール（下水）"> <img src="icons/dm-4161.svg" width="22" height="22" title="マンホール（水道）"> <img src="icons/dm-4215.svg" width="22" height="22" title="消火栓"> <img src="icons/dm-4216.svg" width="22" height="22" title="消火栓 立型"> <img src="icons/dm-4237.svg" width="22" height="22" title="照明灯"> <img src="icons/dm-4238.svg" width="22" height="22" title="防犯灯"> | add road invention icon |
| 2026-01-27 | 58 | <img src="icons/dm-3401.svg" width="22" height="22" title="門"> <img src="icons/dm-3509.svg" width="22" height="22" title="郵便局"> <img src="icons/dm-3510.svg" width="22" height="22" title="森林管理署"> <img src="icons/dm-3514.svg" width="22" height="22" title="警察署"> <img src="icons/dm-3516.svg" width="22" height="22" title="消防署"> <img src="icons/dm-3521.svg" width="22" height="22" title="神社"> <img src="icons/dm-3522.svg" width="22" height="22" title="寺院"> <img src="icons/dm-3523.svg" width="22" height="22" title="キリスト教会"> <img src="icons/dm-3525.svg" width="22" height="22" title="幼稚園・保育園"> <img src="icons/dm-3526.svg" width="22" height="22" title="公会堂・公民館"> <img src="icons/dm-3532.svg" width="22" height="22" title="病院"> <img src="icons/dm-3534.svg" width="22" height="22" title="銀行"> <img src="icons/dm-3536.svg" width="22" height="22" title="協同組合"> <img src="icons/dm-3545.svg" width="22" height="22" title="倉庫"> <img src="icons/dm-3548.svg" width="22" height="22" title="工場"> <img src="icons/dm-3550.svg" width="22" height="22" title="変電所"> <img src="icons/dm-3556.svg" width="22" height="22" title="揚排水ポンプ場"> <img src="icons/dm-4201.svg" width="22" height="22" title="墓碑"> <img src="icons/dm-4202.svg" width="22" height="22" title="記念碑"> <img src="icons/dm-4203.svg" width="22" height="22" title="立像"> <img src="icons/dm-4204.svg" width="22" height="22" title="路傍祠"> <img src="icons/dm-4205.svg" width="22" height="22" title="灯ろう"> <img src="icons/dm-4207.svg" width="22" height="22" title="鳥居"> <img src="icons/dm-4219.svg" width="22" height="22" title="坑口"> <img src="icons/dm-4228.svg" width="22" height="22" title="起重機"> <img src="icons/dm-4234.svg" width="22" height="22" title="煙突"> <img src="icons/dm-4235.svg" width="22" height="22" title="高塔"> <img src="icons/dm-4236.svg" width="22" height="22" title="電波塔"> <img src="icons/dm-5105.svg" width="22" height="22" title="湖池"> <img src="icons/dm-5226.svg" width="22" height="22" title="滝"> <img src="icons/dm-5228.svg" width="22" height="22" title="水門"> <img src="icons/dm-5241.svg" width="22" height="22" title="流水方向"> <img src="icons/dm-6214.svg" width="22" height="22" title="園庭"> <img src="icons/dm-6215.svg" width="22" height="22" title="墓地"> <img src="icons/dm-6216.svg" width="22" height="22" title="材料置場"> <img src="icons/dm-6226.svg" width="22" height="22" title="史跡・名勝・天然記念物"> <img src="icons/dm-6311.svg" width="22" height="22" title="田"> <img src="icons/dm-6313.svg" width="22" height="22" title="畑"> <img src="icons/dm-6317.svg" width="22" height="22" title="桑畑"> <img src="icons/dm-6319.svg" width="22" height="22" title="果樹園"> <img src="icons/dm-6321.svg" width="22" height="22" title="その他の樹木畑"> <img src="icons/dm-6322.svg" width="22" height="22" title="牧草地"> <img src="icons/dm-6323.svg" width="22" height="22" title="芝地"> <img src="icons/dm-6331.svg" width="22" height="22" title="広葉樹林"> <img src="icons/dm-6332.svg" width="22" height="22" title="針葉樹林"> <img src="icons/dm-6333.svg" width="22" height="22" title="竹林"> <img src="icons/dm-6334.svg" width="22" height="22" title="荒地"> <img src="icons/dm-6336.svg" width="22" height="22" title="しの地（笹地）"> <img src="icons/dm-6338.svg" width="22" height="22" title="湿地"> <img src="icons/dm-6340.svg" width="22" height="22" title="砂れき地"> <img src="icons/dm-7202.svg" width="22" height="22" title="雨裂"> <img src="icons/dm-7213.svg" width="22" height="22" title="散岩"> <img src="icons/dm-7301.svg" width="22" height="22" title="三角点"> <img src="icons/dm-7302.svg" width="22" height="22" title="水準点"> <img src="icons/dm-7308.svg" width="22" height="22" title="電子基準点"> <img src="icons/dm-7312.svg" width="22" height="22" title="図化機測定による標高点"> <img src="icons/dm-8199.svg" width="22" height="22" title="指示点"> <img src="icons/dm-9303210.svg" width="22" height="22" title="警報遮断機_道路"> | Add topographic map icon |
| 2024-09-03 | 1 | <img src="icons/map-pin.svg" width="22" height="22" title="マップピン"> | Initial commit |

コードと名称は [docs/icon-list.md](docs/icon-list.md) を参照。

<!-- icon-history:end -->

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

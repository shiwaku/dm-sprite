# 公共測量成果スプライト

公共測量標準図式（作業規程の準則 付録7）の地図記号を、MapLibre 向けスプライトシートとして配信しています。

## 使う側へ — 分類コードとアイコンキーの対応

**標準図式のコードは `dm-<4桁コード>` をそのまま引いてください。** 全国共通ですので、どの自治体のデータでも同じキーで正しい記号が表示されます。

```js
'icon-image': ['concat', 'dm-', ['get', '分類コード']]   // 4132 → dm-4132
```

**標準図式に無いコード（自治体・ベンダ独自の拡張DMコード）は、この方法では引かないようにお願いします。** 標準から外れた枠は提供元ごとに意味が異なるため、同じ `4191` でも自治体が変われば別の地物を指します。標準か拡張かは、[`data/standard-codes.csv`](data/standard-codes.csv)（453コード）に在るかどうかで機械的に判別できます。

**判定に使えるのはこの `standard-codes.csv` だけです。** [`data/symbols.csv`](data/symbols.csv)（372コード）は「どのコードにアイコンが要るか」を判定するための別の表で、注記（81xx・82xx）と「未分類」行を持たないため、標準か拡張かの判定に使うと拡張と誤判定します。

### 拡張コードをどう引くか

拡張コードのアイコンには、キーに提供元の区画が入ります。

```
dm-4132              標準図式。全国共通
dm-toyonaka-4143     拡張DM。豊中市の運用
dm-ext1-9109         拡張DM。提供元が未特定のもの
```

**ただし、拡張コードのすべてがこのスプライトに入るわけではありません。** 既存のアイコンと意匠が同じ場合は、こちらには追加せず、**利用側で既存のキーを指していただく**形になります。同じ絵を別のキーで二重に配らないためです。

| 図面の意匠 | アイコンキー | 対応の記録 |
|---|---|---|
| 既存アイコンと同じ | 既存のキーを指す（例 `dm-4161`） | **利用側のプロジェクトに記録してください** |
| 既存に無い意匠 | `dm-<提供元>-<コード>` として追加をご依頼ください | このリポジトリに記録されます |

**実例をご紹介します。** 豊中市の道路台帳平面図では、拡張コード `4191` が ㊌（丸囲みの「水」）で描かれています。この意匠は標準図式の `4161` マンホール（水道）とまったく同じで、図面も両者を記号で描き分けていません。そのため `dm-toyonaka-4191` は作らず、**利用側で `4191` の地物に `dm-4161` を指定していただきます**。

```js
// 利用側のコード対応表（豊中市の道路台帳平面図）
const ICON = {
  '4191': 'dm-4161',   // 図面では ㊌。標準の 4161 マンホール（水道）と同一意匠で
                       // 描かれており、図面が両者を記号で描き分けていないため。
                       // 出典: 豊中市サンプル図郭57-08 DM-_57-08.pdf
};
```

**この対応と根拠は、利用側のプロジェクトに書き残してください。** どのコードをどのアイコンで代替したかは、そのデータを扱うプロジェクトごとのご判断になるためです。スプライト側では「どんなアイコンが存在するか」のみを提供しています。

意匠が既存と同じかどうかは、次のコマンドで機械的にご確認いただけます。

```bash
python3 tools/verify_shapes.py --similar 図面から起こした案.svg
```

## アイコンを追加する

| ドキュメント | 内容 |
|---|---|
| [docs/icon-list.md](docs/icon-list.md) | 収録アイコンの一覧と追加履歴 |
| [docs/symbol-coverage.md](docs/symbol-coverage.md) | 図式に定義された記号のうち、アイコンが必要なのは何件で残りは何件かの台帳 |
| [data/shape-baseline.csv](data/shape-baseline.csv) | 各アイコンが図式の形と一致しているかの判定（`verify_shapes.py --check` が突き合わせます） |
| [data/standard-codes.csv](data/standard-codes.csv) | 標準図式の全453コード。標準か拡張（自治体・ベンダ独自）かの判定に使います |
| [docs/icon-authoring-guide.md](docs/icon-authoring-guide.md) | 標準図式から SVG を起こす手順（図式の読み取り・大きさの決め方・作図・検証・公開） |
| [docs/svg-design-spec.md](docs/svg-design-spec.md) | SVG 設計基準（64×64・単色・ストローク不使用など） |

作図と検証には、`tools/` のスクリプトをお使いください。

```bash
python3 tools/gen_icons.py --install   # 作図ヘルパと作例。icons/ に書き出す
python3 tools/inspect_icons.py dm-7212 # bbox・中心・線幅を実測
python3 tools/gen_icon_list.py         # docs/icon-list.md を再生成
python3 tools/gen_symbol_coverage.py   # docs/symbol-coverage.md を再生成
python3 tools/verify_shapes.py --check # 形が図式から起こした基準形状と一致しているか
python3 tools/verify_shapes.py --similar 案.svg  # 同じ形の既存アイコンが無いか
```

アイコンを追加された際は、[`data/icons.csv`](data/icons.csv)（名称のマスタ）に行を足していただき、コミット後に `gen_icon_list.py` を実行して一覧を更新してください。カバレッジ側は `gen_symbol_coverage.py` で更新できます。

図式の台帳 [`data/symbols.csv`](data/symbols.csv) は図式 PDF から起こしたもので、作り直すときのみ PDF が必要です。

```bash
python3 tools/extract_symbol_table.py ~/公共測量標準図式.pdf     # data/symbols.csv と data/standard-codes.csv を再抽出
python3 tools/dump_zushiki_geometry.py ~/公共測量標準図式.pdf    # data/zushiki-geometry.json を再抽出
```

PDF は国土地理院が公開している[作業規程の準則 付録7 公共測量標準図式](https://www.gsi.go.jp/common/000258741.pdf)です。サイズが大きいため、リポジトリには置いていません。

---

## 更新履歴

<!-- icon-history:start -->

収録数は **167件** です。日付は git 履歴（そのファイルが追加されたコミット）によります。

| 追加日 | 件数 | 追加したアイコン | 内容 |
|---|---:|---|---|
| 2026-08-13 | 19 | <img src="icons/dm-4119.svg" width="22" height="22" title="有線柱"> <img src="icons/dm-4206.svg" width="22" height="22" title="狛犬"> <img src="icons/dm-4208.svg" width="22" height="22" title="自然災害伝承碑"> <img src="icons/dm-4211.svg" width="22" height="22" title="官民境界杭"> <img src="icons/dm-4217.svg" width="22" height="22" title="地下換気孔"> <img src="icons/dm-4223.svg" width="22" height="22" title="噴水"> <img src="icons/dm-4224.svg" width="22" height="22" title="井戸"> <img src="icons/dm-4225.svg" width="22" height="22" title="油井・ガス井"> <img src="icons/dm-4226.svg" width="22" height="22" title="貯水槽"> <img src="icons/dm-4227.svg" width="22" height="22" title="肥料槽"> <img src="icons/dm-4232.svg" width="22" height="22" title="給水塔"> <img src="icons/dm-4233.svg" width="22" height="22" title="火の見"> <img src="icons/dm-4242.svg" width="22" height="22" title="航空灯台"> <img src="icons/dm-4245.svg" width="22" height="22" title="ヘリポート"> <img src="icons/dm-4252.svg" width="22" height="22" title="流量観測所"> <img src="icons/dm-4253.svg" width="22" height="22" title="雨量観測所"> <img src="icons/dm-4254.svg" width="22" height="22" title="水質観測所"> <img src="icons/dm-4255.svg" width="22" height="22" title="波浪観測所"> <img src="icons/dm-4256.svg" width="22" height="22" title="風向・風速観測所"> | feat: 小物体（レイヤ42）の未作成アイコン19件を追加する |
| 2026-08-13 | 7 | <img src="icons/dm-6221.svg" width="22" height="22" title="噴火口・噴気口"> <img src="icons/dm-6223.svg" width="22" height="22" title="陵墓"> <img src="icons/dm-6224.svg" width="22" height="22" title="古墳"> <img src="icons/dm-6225.svg" width="22" height="22" title="城・城跡"> <img src="icons/dm-6312.svg" width="22" height="22" title="はす田"> <img src="icons/dm-6315.svg" width="22" height="22" title="パイナップル畑"> <img src="icons/dm-6316.svg" width="22" height="22" title="わさび畑"> | feat: 形が図式と一致していることを機械保証する仕組みと、土地利用等7件を追加する |
| 2026-08-13 | 19 | <img src="icons/dm-3503.svg" width="22" height="22" title="官公署"> <img src="icons/dm-3504.svg" width="22" height="22" title="裁判所"> <img src="icons/dm-3505.svg" width="22" height="22" title="検察庁"> <img src="icons/dm-3507.svg" width="22" height="22" title="税務署"> <img src="icons/dm-3508.svg" width="22" height="22" title="税関"> <img src="icons/dm-3511.svg" width="22" height="22" title="測候所"> <img src="icons/dm-3512.svg" width="22" height="22" title="地方整備局事務所"> <img src="icons/dm-3513.svg" width="22" height="22" title="出張所"> <img src="icons/dm-3517.svg" width="22" height="22" title="職業安定所（ハローワーク）"> <img src="icons/dm-3518.svg" width="22" height="22" title="土木事務所"> <img src="icons/dm-3524.svg" width="22" height="22" title="学校"> <img src="icons/dm-3527.svg" width="22" height="22" title="博物館"> <img src="icons/dm-3528.svg" width="22" height="22" title="図書館"> <img src="icons/dm-3529.svg" width="22" height="22" title="美術館"> <img src="icons/dm-3539.svg" width="22" height="22" title="デパート"> <img src="icons/dm-3549.svg" width="22" height="22" title="発電所"> <img src="icons/dm-3552.svg" width="22" height="22" title="浄水場"> <img src="icons/dm-3553.svg" width="22" height="22" title="揚水機場"> <img src="icons/dm-3557.svg" width="22" height="22" title="排水機場"> | feat: 建物等（レイヤ35）の未作成アイコン19件を追加する |
| 2026-08-13 | 1 | <img src="icons/dm-2235.svg" width="22" height="22" title="雨水桝"> | feat: 22-35 雨水桝のアイコンを追加する |
| 2026-08-12 | 8 | <img src="icons/dm-2221.svg" width="22" height="22" title="バス停"> <img src="icons/dm-2246.svg" width="22" height="22" title="信号灯"> <img src="icons/dm-2261.svg" width="22" height="22" title="電話ボックス"> <img src="icons/dm-2262.svg" width="22" height="22" title="郵便ポスト"> <img src="icons/dm-3559.svg" width="22" height="22" title="公衆便所"> <img src="icons/dm-4132.svg" width="22" height="22" title="電話柱"> <img src="icons/dm-4142.svg" width="22" height="22" title="電力柱"> <img src="icons/dm-7306.svg" width="22" height="22" title="公共基準点（多角点等）"> | feat: 道路台帳平面図で使う標準図式アイコン8件を追加する |
| 2026-08-11 | 6 | <img src="icons/dm-2219.svg" width="22" height="22" title="道路のトンネル"> <img src="icons/dm-3519.svg" width="22" height="22" title="役場支所及び出張所"> <img src="icons/dm-3531.svg" width="22" height="22" title="保健所"> <img src="icons/dm-5227.svg" width="22" height="22" title="せき"> <img src="icons/dm-6335.svg" width="22" height="22" title="はい松地"> <img src="icons/dm-7212.svg" width="22" height="22" title="露岩"> | 不足していた標準図式アイコン6件を追加 |
| 2026-02-26 | 8 | <img src="icons/dm-4239.svg" width="22" height="22" title="風車"> <img src="icons/dm-5221.svg" width="22" height="22" title="渡船発着所"> <img src="icons/dm-6314.svg" width="22" height="22" title="さとうきび畑"> <img src="icons/dm-6337.svg" width="22" height="22" title="やし科樹林"> <img src="icons/dm-7206.svg" width="22" height="22" title="洞口"> <img src="icons/dm-7303.svg" width="22" height="22" title="多角点等"> <img src="icons/dm-7304.svg" width="22" height="22" title="公共基準点（三角点）"> <img src="icons/dm-7305.svg" width="22" height="22" title="公共基準点（水準点）"> | 不足アイコンを追加 |
| 2026-02-20 | 9 | <img src="icons/dm-2242.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-2243.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-2244.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-ext1-2245.svg" width="22" height="22" title="道路標識_道路"> <img src="icons/dm-ext1-9101100.svg" width="22" height="22" title="起終点_道路（起点）"> <img src="icons/dm-ext1-9101200.svg" width="22" height="22" title="起終点_道路（終点）"> <img src="icons/dm-ext1-9109.svg" width="22" height="22" title="官民境界杭_道路"> <img src="icons/dm-ext1-9303210.svg" width="22" height="22" title="警報遮断機_道路"> <img src="icons/dm-ext1-9303220.svg" width="22" height="22" title="警報遮断機_道路"> | add road  icons |
| 2026-02-10 | 19 | <img src="icons/dm-3401.svg" width="22" height="22" title="門"> <img src="icons/dm-3515.svg" width="22" height="22" title="交番・駐在所"> <img src="icons/dm-3530.svg" width="22" height="22" title="老人ホーム"> <img src="icons/dm-3546.svg" width="22" height="22" title="火薬庫"> <img src="icons/dm-3560.svg" width="22" height="22" title="ガソリンスタンド"> <img src="icons/dm-4221.svg" width="22" height="22" title="独立樹（広葉樹）"> <img src="icons/dm-4222.svg" width="22" height="22" title="独立樹（針葉樹）"> <img src="icons/dm-4231.svg" width="22" height="22" title="タンク"> <img src="icons/dm-4241.svg" width="22" height="22" title="灯台"> <img src="icons/dm-4243.svg" width="22" height="22" title="灯標"> <img src="icons/dm-4251.svg" width="22" height="22" title="水位観測所"> <img src="icons/dm-5232.svg" width="22" height="22" title="透過水制"> <img src="icons/dm-6212.svg" width="22" height="22" title="駐車場"> <img src="icons/dm-6217.svg" width="22" height="22" title="太陽光発電設備"> <img src="icons/dm-6222.svg" width="22" height="22" title="温泉・鉱泉"> <img src="icons/dm-6318.svg" width="22" height="22" title="茶畑"> <img src="icons/dm-7201.svg" width="22" height="22" title="土がけ"> <img src="icons/dm-7211.svg" width="22" height="22" title="岩がけ"> <img src="icons/dm-7311.svg" width="22" height="22" title="標石を有しない標高点"> | add dm icons |
| 2026-01-30 | 14 | <img src="icons/dm-2238.svg" width="22" height="22" title="並木"> <img src="icons/dm-2239.svg" width="22" height="22" title="植樹"> <img src="icons/dm-2253.svg" width="22" height="22" title="カーブミラー"> <img src="icons/dm-4101.svg" width="22" height="22" title="マンホール（未分類）"> <img src="icons/dm-4111.svg" width="22" height="22" title="マンホール（共同溝）"> <img src="icons/dm-4121.svg" width="22" height="22" title="マンホール（ガス）"> <img src="icons/dm-4131.svg" width="22" height="22" title="マンホール（電話）"> <img src="icons/dm-4141.svg" width="22" height="22" title="マンホール（電気）"> <img src="icons/dm-4151.svg" width="22" height="22" title="マンホール（下水）"> <img src="icons/dm-4161.svg" width="22" height="22" title="マンホール（水道）"> <img src="icons/dm-4215.svg" width="22" height="22" title="消火栓"> <img src="icons/dm-4216.svg" width="22" height="22" title="消火栓 立型"> <img src="icons/dm-4237.svg" width="22" height="22" title="照明灯"> <img src="icons/dm-4238.svg" width="22" height="22" title="防犯灯"> | add road invention icon |
| 2026-01-27 | 56 | <img src="icons/dm-3509.svg" width="22" height="22" title="郵便局"> <img src="icons/dm-3510.svg" width="22" height="22" title="森林管理署"> <img src="icons/dm-3514.svg" width="22" height="22" title="警察署"> <img src="icons/dm-3516.svg" width="22" height="22" title="消防署"> <img src="icons/dm-3521.svg" width="22" height="22" title="神社"> <img src="icons/dm-3522.svg" width="22" height="22" title="寺院"> <img src="icons/dm-3523.svg" width="22" height="22" title="キリスト教会"> <img src="icons/dm-3525.svg" width="22" height="22" title="幼稚園・保育園"> <img src="icons/dm-3526.svg" width="22" height="22" title="公会堂・公民館"> <img src="icons/dm-3532.svg" width="22" height="22" title="病院"> <img src="icons/dm-3534.svg" width="22" height="22" title="銀行"> <img src="icons/dm-3536.svg" width="22" height="22" title="協同組合"> <img src="icons/dm-3545.svg" width="22" height="22" title="倉庫"> <img src="icons/dm-3548.svg" width="22" height="22" title="工場"> <img src="icons/dm-3550.svg" width="22" height="22" title="変電所"> <img src="icons/dm-3556.svg" width="22" height="22" title="揚排水ポンプ場"> <img src="icons/dm-4201.svg" width="22" height="22" title="墓碑"> <img src="icons/dm-4202.svg" width="22" height="22" title="記念碑"> <img src="icons/dm-4203.svg" width="22" height="22" title="立像"> <img src="icons/dm-4204.svg" width="22" height="22" title="路傍祠"> <img src="icons/dm-4205.svg" width="22" height="22" title="灯ろう"> <img src="icons/dm-4207.svg" width="22" height="22" title="鳥居"> <img src="icons/dm-4219.svg" width="22" height="22" title="坑口"> <img src="icons/dm-4228.svg" width="22" height="22" title="起重機"> <img src="icons/dm-4234.svg" width="22" height="22" title="煙突"> <img src="icons/dm-4235.svg" width="22" height="22" title="高塔"> <img src="icons/dm-4236.svg" width="22" height="22" title="電波塔"> <img src="icons/dm-5105.svg" width="22" height="22" title="湖池"> <img src="icons/dm-5226.svg" width="22" height="22" title="滝"> <img src="icons/dm-5228.svg" width="22" height="22" title="水門"> <img src="icons/dm-5241.svg" width="22" height="22" title="流水方向"> <img src="icons/dm-6214.svg" width="22" height="22" title="園庭"> <img src="icons/dm-6215.svg" width="22" height="22" title="墓地"> <img src="icons/dm-6216.svg" width="22" height="22" title="材料置場"> <img src="icons/dm-6226.svg" width="22" height="22" title="史跡・名勝・天然記念物"> <img src="icons/dm-6311.svg" width="22" height="22" title="田"> <img src="icons/dm-6313.svg" width="22" height="22" title="畑"> <img src="icons/dm-6317.svg" width="22" height="22" title="桑畑"> <img src="icons/dm-6319.svg" width="22" height="22" title="果樹園"> <img src="icons/dm-6321.svg" width="22" height="22" title="その他の樹木畑"> <img src="icons/dm-6322.svg" width="22" height="22" title="牧草地"> <img src="icons/dm-6323.svg" width="22" height="22" title="芝地"> <img src="icons/dm-6331.svg" width="22" height="22" title="広葉樹林"> <img src="icons/dm-6332.svg" width="22" height="22" title="針葉樹林"> <img src="icons/dm-6333.svg" width="22" height="22" title="竹林"> <img src="icons/dm-6334.svg" width="22" height="22" title="荒地"> <img src="icons/dm-6336.svg" width="22" height="22" title="しの地（笹地）"> <img src="icons/dm-6338.svg" width="22" height="22" title="湿地"> <img src="icons/dm-6340.svg" width="22" height="22" title="砂れき地"> <img src="icons/dm-7202.svg" width="22" height="22" title="雨裂"> <img src="icons/dm-7213.svg" width="22" height="22" title="散岩"> <img src="icons/dm-7301.svg" width="22" height="22" title="三角点"> <img src="icons/dm-7302.svg" width="22" height="22" title="水準点"> <img src="icons/dm-7308.svg" width="22" height="22" title="電子基準点"> <img src="icons/dm-7312.svg" width="22" height="22" title="図化機測定による標高点"> <img src="icons/dm-8199.svg" width="22" height="22" title="指示点"> | Add topographic map icon |
| 2024-09-03 | 1 | <img src="icons/map-pin.svg" width="22" height="22" title="マップピン"> | Initial commit |

コードと名称は [docs/icon-list.md](docs/icon-list.md) をご参照ください。

<!-- icon-history:end -->

---

## ビルドと公開

```bash
npm install
npm run build   # _site/ に sprite.png / sprite.json / sprite@2x.png / sprite@2x.json の4ファイルを生成
npm run start   # ビルドしてローカルサーバーを起動（http://localhost:8080）
```

`main` に push すると、GitHub Actions がビルドして GitHub Pages にデプロイします。
公開先は `https://<GitHub username>.github.io/<repository name>/sprite.png` ほか、上記の4ファイルです。

MapLibre に複数のスプライトシートを読み込ませる方法は、[公式ドキュメント](https://maplibre.org/maplibre-style-spec/sprite/#multiple-sprite-sources) をご参照ください。

# SVG 設計基準

> この基準に沿った具体的な作成手順は [アイコン作成ガイド](icon-authoring-guide.md) を参照。

## ファイル形式

- フォーマット：SVG
- 文字コード：UTF-8

## キャンバスサイズ

```xml
<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
```

| 属性 | 値 |
|---|---|
| width | 64px |
| height | 64px |
| viewBox | 0 0 64 64 |
| fill（ルート要素） | none |

## カラー

単色（黒）のみ使用。パスに `fill="black"` を指定する。

```xml
<path d="..." fill="black"/>
```

- カラーコード：`black`（`#000000` 相当）
- グラデーション・複数色は使用しない
- ストロークは原則使用しない（パスで形状を表現する）

## デザイン方針

- 公共測量標準図式の図式定義を参考にシンプルに SVG 化する
- 64×64px のキャンバス内に収まるように設計する
- 視認性を確保するため、細すぎる線（1px 未満相当）は避ける
- 記号の中心はキャンバス中央（32, 32）付近に配置する

## ファイル配置

```
icons/
  dm-{コード}.svg
```

## SVG サンプル（dm-7301.svg 三角点）

```xml
<svg width="64" height="64" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M31.17 23.81L21.8 40.03H40.53L31.16 23.81H31.17Z..." fill="black"/>
</svg>
```

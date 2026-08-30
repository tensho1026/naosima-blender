# Naoshima Blender Generator

香川県・直島の **実在する地理データ** から、Blender 3D シーンを自動生成するツールです。

手作業のモデリングではなく、次で島全体（地形・海岸・海・OSM建物・道路・森林・簡易ランドマーク）を組み立てます。

```bash
blender --background --python generate.py
# または
./generate-naoshima.sh
```

成果物: `output/naoshima.blend`

## プロジェクト概要

- 対象: 直島本島（宮浦・宮浦港・本村・積浦・琴弾地・ベネッセハウス周辺・地中美術館周辺・李禹煥美術館周辺・直島新美術館周辺・海岸・山林を Empty / 地区半径で識別）
- 将来: `generate_location.py --lat --lon --radius` で豊島・男木島・女木島などへ流用できる座標設定
- 方針: 想像で島の形や街を作らない。取れない情報は `UNKNOWN` / 推定と明記する

## 使用データ / データ取得元

| 種類 | 取得元 | 利用方法 |
|------|--------|----------|
| 標高 DEM | 国土地理院 標高タイル（`dem`、ズーム14、約10 m） | `https://cyberjapandata.gsi.go.jp/xyz/dem/{z}/{x}/{y}.txt` |
| 海岸・水面 | DEM の無効値（海）+ OSM `natural=coastline` | 地形メッシュの陸域マスク |
| 建物・道路・土地利用・森林 | OpenStreetMap Overpass API | 建物ポリゴン押し出し、道路ストリップ、森林範囲 |
| 地区・港の座標 | 公開地名資料 + OSM 名称マッチ | 宮浦港・本村港は公開ガゼット、李禹煥美術館は公開 POI。その他は OSM 優先、なければ APPROXIMATE |
| 海の駅なおしま寸法 | 直島町公式（大屋根 約70×52 m） | Approximate Landmark の根拠。BIM ではない |
| 景観ルール | 直島町・香川県観光・ベネッセアートサイト等の **公開文章** | 本村=焼杉・瓦・城下町の細い街路。宮浦=港・SANAA の大屋根・比較的新しい建物。写真ファイルはリポジトリに保存しない |

仕様: [標高タイルの詳細仕様](https://cyberjapandata.gsi.go.jp/development/demtile.html)

地理院タイルの利用は出典明示（国土地理院 / 地理院タイル）で申請不要、との案内に従っています。  
OSM は [ODbL](https://www.openstreetmap.org/copyright) です。

## Blender バージョン

開発・CLI 確認: **Blender 4.5.13 LTS**（`bpy` 4.5）。  
4.2 系でも動く想定ですが、Geometry Nodes のソケット名は 4.5 で確認しています。

```bash
blender --version
```

## セットアップ

1. [Blender 4.5 LTS](https://www.blender.org/download/) をインストールし、`blender` が PATH にあること
2. 追加 pip パッケージは **不要**（標準ライブラリ + Blender 同梱の numpy）
3. 初回は DEM タイルと Overpass のためネット接続が必要

```bash
chmod +x generate-naoshima.sh render-preview.sh
```

Mac: Blender アプリのバイナリを使う例

```bash
export BLENDER="/Applications/Blender.app/Contents/MacOS/Blender"
./generate-naoshima.sh
```

## 実行方法

```bash
blender --background --python generate.py
./generate-naoshima.sh
./generate-naoshima.sh --lod 0          # 軽いプレビュー
./generate-naoshima.sh --render-previews
./render-preview.sh
```

他地域（実験）:

```bash
blender --background --python generate_location.py -- --lat 34.48 --lon 134.08 --radius 3000 --id teshima
```

## DEM 取得方法

1. `src/config.py` の `NAOSHIMA_BBOX`（南, 西, 北, 東）から Web メルカトルタイル番号を計算
2. 国土地理院 `dem` レイヤのテキスト標高タイルをダウンロード
3. `data/dem/naoshima/dem/14/{x}_{y}.txt` にキャッシュ
4. 無効値 `e` は海 / 欠測（NaN）。陸域だけメッシュ化
5. 水平・鉛直とも 1 Blender 単位 = 1 m（`TERRAIN_SCALE`）
6. LOD 0/1 では間引き。より細かい 5 m は `dem_layer="dem5a"` と `dem_zoom=15`（重い）

手動でタイルを置き換えても、同じファイル名なら再ダウンロードしません。

## OSM 取得方法

Overpass クエリ（建物・道路・landuse・natural・leisure・名称ノード等）を bbox で実行し、

```text
data/osm/naoshima.osm.json
```

に保存します（Overpass の JSON。拡張子はキャッシュ用）。  
ミラー: `overpass-api.de` → 失敗時 `overpass.kumi.systems`

キャッシュがあれば API は叩きません。更新するときはそのファイルを削除してください。

## 自動生成フロー

1. 空シーン
2. GSI DEM → Terrain
3. 海面 Plane + Water マテリアル
4. OSM / DEM 海岸
5. OSM building をポリゴン押し出し。高さは `height` / `building:levels`、無ければ推定
6. OSM highway を地形に沿った帯メッシュ。幅は道路種別の推定値
7. forest/wood 範囲に点をばらまき、Geometry Nodes で低ポリ木をインスタンス
8. 地区ルール（本村 / 宮浦 / その他）で壁・屋根マテリアル
9. ランドマーク: `assets/landmarks/{key}.blend` があれば置換、なければ Approximate Landmark またはアートの Placeholder
10. Sun + Nishita Sky、確認用カメラ
11. `output/naoshima.blend` 保存。`--render-previews` で PNG

## キャッシュについて

| パス | 内容 |
|------|------|
| `data/dem/` | GSI 標高タイル |
| `data/osm/` | Overpass JSON |
| `data/cache/` | 予備 |
| `output/` | `.blend` とプレビュー（git 対象外） |

## 生成物

- `output/naoshima.blend`
- `output/previews/overview.png` ほか（レンダー時）
- コレクション: Terrain, Ocean, Coastline, Buildings, Roads, Vegetation, Landmarks, DistrictMarkers, Cameras, Lighting, TreeAssets

## LOD

| LOD | 用途 |
|-----|------|
| 0 | 島全体。地形間引き大、歩道省略、木を抑制 |
| 1 | 既定。地区表示向け |
| 2 | 近距離。点群・道路サンプルを密に（窓メッシュは作らない） |

遠景の住宅に窓枠などの細かいメッシュは生成しません。

## 実データ部分

- 島の標高フィールド（GSI）
- OSM の建物外形・道路中心線・土地利用・自然・海岸ウェイ（ある範囲）
- OSM / 公開資料で取れた施設の位置
- 海の駅の屋根の公表おおよその平面寸法（70×52 m）

## 推定している部分 / UNKNOWN

- **建物高さ**: OSM に height / levels が無い場合、用途別階数 × 3 m または既定 6 m（`src/config.py`）
- **道路幅**: 日本の島しょ部の典型値。OSM `width=*` はほぼ未使用
- **本村の切妻屋根**: 景観文献に基づくスタイル推定。個別家屋の実測ではない
- **積浦・琴弾地・ベネッセ・地中・新美術館の中心**: 公開住所・OSM 名称で補正。失敗時は APPROXIMATE。取れなければログに UNKNOWN
- **地中美術館**: 大半が地下（ベネッセ公式）。地上は低いコンクリートの Approximate Landmark のみ。内部形状 UNKNOWN
- **安藤・SANAA 建築の正確な 3D**: 公開図面がないため精密モデルは作らない
- **森林が OSM に無いセル**: 標高フォールバック（ログに明示）
- **岩の配置**: 急傾斜の DEM 上のランダム。地質図ではない
- **アート作品**: 赤かぼちゃ等は **位置マーカーのみ**。形状はコピーしない
- **写真テクスチャ**: 著作権のある画像は保存・再配布しない。マテリアルはプロシージャル

## 地域別景観（文献ベースのルール）

公開情報の要約（AI の「直島風」想像ではない）:

- **本村**: 城下町由来の街区、江戸期民家が残る、焼杉板の外壁が多い、瓦屋根、細い道、塀のある屋敷（ベネッセ教育情報の本村記事、香川県観光の集落説明）
- **宮浦**: 島の玄関・宮浦港。海の駅なおしまは SANAA、薄い大きな鉄板屋根とガラスの箱（直島町公式）。港湾・店舗・比較的新しい住宅が混在
- **積浦**: 漁港集落（町・プレスキット）。観光拠点より生活・漁港側
- **琴弾地**: ベネッセハウス住所。南の海岸・美術館エリア
- **その他**: OSM のまま + 現代壁/屋根

## ランドマークとアセット差し替え

`assets/landmarks/` に次のファイル名で `.blend` を置くと、Approximate の代わりに append します。

- `marine_station.blend`
- `chichu.blend`
- `lee_ufan.blend`
- `benesse_house.blend`
- `new_museum.blend`

## 著作権・ライセンス上の注意

- 国土地理院タイル: 出典を明記して利用。成果の再配布時も出典を残すこと
- OpenStreetMap: ODbL。派生データベースとしての表示が必要な場合あり
- 草間彌生作品・安藤建築・SANAA 建築などの **著作物を精密に複製しない**
- 観光写真をプロジェクトへコピーしない
- 本リポジトリの **コード** は生成ツールであり、直島の公式 3D ではありません

## 既知の制限

- Overpass / 地理院サーバの一時障害で初回取得が失敗することがある（キャッシュ後はオフライン可）
- OSM の欠落・古さはそのままシーンに出る
- 北の製錬所エリアは OSM industrial 次第で簡略
- Geometry Nodes の木は低ポリ 3 種。樹種の現地同定はしていない
- CPU Cycles のプレビューはサンプル数が少なくノイズが残る
- MacBook 向けにメッシュを間引いているため、登山道スケールの微地形は出ない
- `read_factory_settings` でアドオン状態はリセットされる

## 今後の改善案

- `dem5a` ズーム15 と島マスクのポリゴンクリップ
- OSM の `width` / `roof:shape` / `building:material` の本格反映
- 本村の塀・石垣を landuse から生成
- 手作りランドマーク blend の公式公開モデル（許可がある場合のみ）
- EEVEE Next 用の軽量プレビュー
- 豊島・男木島プリセット

## プロジェクト構成

`src/config.py` に `NAOSHIMA_CENTER_LAT` / `LON` / `BOUNDING_BOX` / `SEA_LEVEL` / `TERRAIN_SCALE` / `TREE_DENSITY` を集約しています。

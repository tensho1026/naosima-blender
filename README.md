# Naoshima Blender Generator

直島の国土地理院DEM・航空写真とOpenStreetMapからBlenderシーンを生成します。
**現状は地理データに基づく再構成であり、全建物の実測による完全再現ではありません。**

## 改善版の生成

Blender 5.2.0 LTSで生成・レンダリングを確認しています。Blender MCPからシーンの確認・コード実行・読み込みができます。シーンを初期化するときもアドオンの設定をリセットしません。

```sh
# 任意: 正確な海岸輪郭のメッシュを前処理する（初回のみ）
python3 -m venv .venv-gis
.venv-gis/bin/python -m pip install -r requirements-gis.txt
.venv-gis/bin/python scripts/prepare_coastal_terrain.py

# 改善版。初回の航空写真取得はネット接続が必要
/Applications/Blender.app/Contents/MacOS/Blender --background --python generate.py -- --refined

# 保存した改善版の4視点をレンダリング
/Applications/Blender.app/Contents/MacOS/Blender --background --python scripts/render_review.py
```

BlenderがPATHにあればアプリの絶対パスを`blender`に置き換えられます。通常の軽量版は`blender --background --python generate.py -- --lod 1`です。

## 保存先

- `output/naoshima.blend`: 既存の生成物。改善作業では保持
- `output/naoshima_refined.blend`: 改善版。航空写真を内包
- `output/refined_previews/`: 全景・宮浦・本村・新美術館の確認画像
- `output/building_audit.json`: 建物ID・高さの根拠・屋根の推定状態
- `output/validation_audit.json`: Blender内の検証結果
- `RECONSTRUCTION_STATUS.md`: 再現範囲と未解決事項

## 改善内容

- OSMの建物外形を保持し、閉じた切妻屋根・基礎・近景用の窓を生成。窓配置は実測ではなく推定
- 高さを地区別に勝手に増減しない。地上階数0の地中美術館を地上に押し出さない
- 海の駅はOSM way 75615686の屋根輪郭を使用。汎用建物との二重生成を防止
- 新美術館の地区位置を本村のOSM POIで補正。公式写真に基づく勾配屋根・黒漆喰を反映（寸法は推定）。部分一致でチケットセンター等を本館にしない
- 中庭付きのOSM multipolygon建物を、中庭を塞がずに生成
- 全国最新写真（シームレス）z16を島全体、z18を宮浦・本村に地理参照付きで適用
- OSMの接続する海岸線を結合してDEMをクリップ。前処理キャッシュがない場合はDEM格子の輪郭へフォールバック
- 森林ポリゴン内に密度に基づく樹木を配置。岩と木のインスタンス候補を分離
- 計画道路・海上の国道30号を除外。道路の上向き法線を修正し、OSM道路幅があれば優先
- アート作品の未制作形状を赤い箱として表示せず、編集用の位置マーカーで保持

## 出典

- 地形・航空写真: **国土地理院 / 地理院タイル** — https://maps.gsi.go.jp/development/ichiran.html
- 標高タイル仕様: https://cyberjapandata.gsi.go.jp/development/demtile.html
- 建物・道路・海岸・土地利用: **© OpenStreetMap contributors (ODbL)** — https://www.openstreetmap.org/copyright
- 海の駅の公表屋根寸法: https://www.town.naoshima.lg.jp/about/shisetsu/seastation.html
- 直島新美術館の立地・外観説明: https://benesse-artsite.jp/nnmoa/art/

航空写真は複数年代の撮影画像を組み合わせたものです。「最新」というレイヤ名は、2026年現在の全建物と一致することを意味しません。撮影時期は個別確認未了です。外観の写真とOSM外形の更新時期が異なる部分があります。

## キャッシュ

`data/dem/`、`data/osm/`は既存地理データです。`data/aerial/`は写真・地理参照メタデータ、`data/cache/coastal_terrain.npz`は海岸クリップ済みメッシュです。OSM・DEMを変更した場合は海岸前処理を再実行してください。Shapelyは前処理専用で、Blender内での生成には不要です。

## 検証

```sh
python3 -m unittest discover -s tests -v
blender --background --python tests/validate_blender_scene.py
```

統合検証は現在の直島OSMキャッシュを対象とし、建物数・地下建築の除外・海の駅の重複排除・高さ保持・道路法線・樹木/岩の分離・写真のUV座標・画像内包を確認します。実景との一致を証明するテストではありません。

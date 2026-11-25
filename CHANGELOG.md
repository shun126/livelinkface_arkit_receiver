# LiveLinkFace ARKit Receiver for Blender

## 20261124-0.5
### Changes
* Drive eye, neck and head bones from the received rotation values (#13)
* Added bone selection, neck/head distribution, scale and per-axis mapping
* Mirror Left/Right now also applies to head and eye rotation
* Write head and eye rotation to custom properties for use with drivers (#13)
* Invert Head Pitch is now on by default, because the received head pitch has the opposite sign to eye pitch
* Removed the debug log printed for every received packet
* Added timelapse recording (#5)
* Added operators to record, clear and clean up facial keys for shape keys and bones (#5)
* Added support for Blender 5.1
* Releases are now created automatically when a tag is pushed, and the zip includes CHANGELOG.md
### 変更点
* 受信した回転値で目・首・頭のボーンを駆動 (#13)
* ボーンの選択、首と頭の配分、倍率、軸ごとのマッピングを追加
* Mirror Left/Right を頭と目の回転にも適用
* 頭と目の回転をドライバー用のカスタムプロパティへ書き出し (#13)
* 受信する頭のピッチは目のピッチと符号が逆のため、Invert Head Pitch を既定でオンに変更
* パケット受信のたびに出ていたデバッグ用ログを削除
* タイムラプス記録を追加 (#5)
* シェイプキーとボーンの表情キーを記録・削除・クリーンアップする機能を追加 (#5)
* Blender 5.1 に対応
* タグの push でリリースを自動作成するようにし、zip に CHANGELOG.md を追加

## 20260911-0.4
### Changes
* Added Mirror Left/Right option to swap left and right blendshape values (thanks to Yunhan Luo)
* Added Blender integration tests and a GitHub Actions workflow
* Added a manually triggered release workflow that publishes a minimal add-on zip
* README is now in English; the Japanese version moved to README.ja.md
### 変更点
* 左右のブレンドシェイプ値を入れ替える Mirror Left/Right オプションを追加（Yunhan Luo さんに感謝）
* Blender 統合テストと GitHub Actions ワークフローを追加
* 最小限のアドオン zip を公開する手動実行のリリースワークフローを追加
* README を英語化し、日本語版を README.ja.md に分離

## 20251103-0.3
### Changes
* Set shape keys for multiple models (#3)
* Received values are now buffered before being applied to shape keys (#3)
### 変更点
* 複数のモデルに対してシェイプキーを設定 (#3)
* 受信した値をバッファしてからシェイプキーへ適用するように変更 (#3)

## 20251024-0.2
### Changes
* Added button to clear shape key (#1)
* Fixed an error when a target object has no shape keys (#1)
### 変更点
* シェイプキーをクリアするボタンを追加 (#1)
* ターゲットオブジェクトにシェイプキーが無い場合のエラーを修正 (#1)

## 20251004-0.1
### Changes
* Pilot release for functional evaluation
* Receive ARKit blendshapes from Live Link Face over UDP and apply them to shape keys
### 変更点
* 機能評価のための試験的なリリース
* Live Link Face から ARKit ブレンドシェイプを UDP で受信し、シェイプキーへ適用

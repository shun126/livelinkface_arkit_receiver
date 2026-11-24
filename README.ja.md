<div align="center">
<h1>LiveLinkFace ARKit Receiver for Blender</h1>

[English](README.md) | 日本語
</div>

[![license](https://img.shields.io/github/license/shun126/livelinkface_arkit_receiver)](https://github.com/shun126/livelinkface_arkit_receiver/blob/main/LICENSE)
[![release](https://img.shields.io/github/v/release/shun126/livelinkface_arkit_receiver)](https://github.com/shun126/livelinkface_arkit_receiver/releases)
[![downloads](https://img.shields.io/github/downloads/shun126/livelinkface_arkit_receiver/total)](https://github.com/shun126/livelinkface_arkit_receiver/releases)
[![stars](https://img.shields.io/github/stars/shun126/livelinkface_arkit_receiver?style=social)](https://github.com/shun126/livelinkface_arkit_receiver/stargazers)
[![Blender Add-on Tests](https://github.com/shun126/livelinkface_arkit_receiver/actions/workflows/blender-tests.yml/badge.svg)](https://github.com/shun126/livelinkface_arkit_receiver/actions/workflows/blender-tests.yml)

![livelinkface_arkit_receiver](https://github.com/shun126/livelinkface_arkit_receiver/wiki/livelinkface_arkit_receiver.gif)

**LiveLinkFace ARKit Receiver** は、iPhone の **Live Link Face** アプリから送信されるフェイシャルトラッキングデータを **Blender** で受信し、モデルのシェイプキーへリアルタイムに適用するアドオンです。

> 🎨 アーティストが「自分の顔でモデルを動かす」ためのシンプルなツールです。

# 🚀 主な特徴

- iPhone Live Link Face から **ARKit ブレンドシェイプ** を UDP で受信
- シェイプキーへ **リアルタイム** に反映（毎秒約60回更新）
- **複数のターゲットオブジェクト** を同時に駆動（顔・まつ毛・歯など）
- 左右のブレンドシェイプ値を入れ替える **Mirror Left/Right** オプション
- ARKit シェイプキーをすべて 0 に戻す **Clear Shape Key Values** ボタン
- **Perfect Sync 対応モデルの検証** に最適
- Blender **4.5** で開発・動作確認済み
- ARKit プロトコルのみ対応（MetaHuman Animator モード、頭部回転・眼球回転には非対応）

# 🧩 インストール方法

1. [Releases](https://github.com/shun126/livelinkface_arkit_receiver/releases) ページから `livelinkface_arkit_receiver-<バージョン>.zip` をダウンロードします。
1. Blender を開き、ダウンロードした .zip ファイルを Blender のウィンドウにドラッグアンドドロップします。
   （**編集 > プリファレンス > アドオン > ディスクからインストール...** からもインストールできます）
1. **LiveLinkFace ARKit Receiver** が有効になっていることを確認します。

# 📡 使用方法

## 1. iPhone 側の設定

* iPhone と PC を同じネットワークに接続します。
* **Live Link Face** アプリを起動し、**Live Link (ARKit)** モードを選択します。
* アプリの Live Link 設定でターゲットを追加します。
  * **IP アドレス**：Blender を実行している PC のローカル IP（例：`192.168.0.10`）
  * **ポート**：`11111`（デフォルト）

## 2. Blender 側の設定

1. 3D ビューポートでサイドバー（`N` キー）を開き、**LiveLinkFace** タブを選択します。
1. **IP** と **Port** を確認します。
   * **IP**：待ち受けるアドレス。通常は `0.0.0.0`（すべてのインターフェース）のままで構いません。
   * **Port**：iPhone アプリで設定したポート番号と同じにします（デフォルト `11111`）。
1. **Target Object** の `+` をクリックし、ARKit 名のシェイプキーを持つメッシュオブジェクトを指定します。
   必要な数だけ追加でき、`-` で選択中の項目を削除できます。
1. **Start LiveLinkFace** をクリックします。

表情を動かすと、Blender 上のモデルにもリアルタイムで反映されます。
受信を止めるには **Stop LiveLinkFace** をクリックします。

## パネルの項目

| 項目 | 説明 |
| --- | --- |
| IP / Port | 待ち受けるアドレスと UDP ポート |
| Target Object | シェイプキーを駆動するオブジェクトのリスト |
| Clear Shape Key Values | ターゲットオブジェクトの ARKit シェイプキーをすべて 0 に戻します。リストが空の場合はアクティブオブジェクトが対象です。停止中のみ実行できます。 |
| Start / Stop LiveLinkFace | 受信の開始・停止 |
| Mirror Left/Right | 左右のブレンドシェイプ値を入れ替えます（例：`eyeBlinkLeft` ⇔ `eyeBlinkRight`）。受信中も切り替え可能です。 |

# 🧰 シェイプキー対応（ARKit 52 キー）

このアドオンは Apple ARKit の 52 ブレンドシェイプ名と **完全に一致する**（大文字・小文字を区別）名前のシェイプキーを駆動します。
それ以外の名前のシェイプキーには影響しないため、Perfect Sync 対応モデルであればそのまま動作します。

| グループ | シェイプキー名 |
| --- | --- |
| 目（左） | `eyeBlinkLeft` `eyeLookDownLeft` `eyeLookInLeft` `eyeLookOutLeft` `eyeLookUpLeft` `eyeSquintLeft` `eyeWideLeft` |
| 目（右） | `eyeBlinkRight` `eyeLookDownRight` `eyeLookInRight` `eyeLookOutRight` `eyeLookUpRight` `eyeSquintRight` `eyeWideRight` |
| 顎 | `jawForward` `jawLeft` `jawRight` `jawOpen` |
| 口 | `mouthClose` `mouthFunnel` `mouthPucker` `mouthLeft` `mouthRight` `mouthSmileLeft` `mouthSmileRight` `mouthFrownLeft` `mouthFrownRight` `mouthDimpleLeft` `mouthDimpleRight` `mouthStretchLeft` `mouthStretchRight` `mouthRollLower` `mouthRollUpper` `mouthShrugLower` `mouthShrugUpper` `mouthPressLeft` `mouthPressRight` `mouthLowerDownLeft` `mouthLowerDownRight` `mouthUpperUpLeft` `mouthUpperUpRight` |
| 眉 | `browDownLeft` `browDownRight` `browInnerUp` `browOuterUpLeft` `browOuterUpRight` |
| 頬 | `cheekPuff` `cheekSquintLeft` `cheekSquintRight` |
| 鼻 | `noseSneerLeft` `noseSneerRight` |
| 舌 | `tongueOut` |

各ブレンドシェイプの詳細は [Apple の ARKit ドキュメント](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation) を参照してください。

# 💡 トラブルシューティング

| 症状 | 原因 | 対処法 |
| --- | --- | --- |
| モデルが動かない | IP 設定の誤り / ネットワークが異なる | iPhone アプリの IP 設定と、iPhone と PC が同じネットワークにいるかを確認 |
| モデルが動かない | ファイアウォールによるブロック | Blender に対してポート（デフォルト `11111`）の UDP 受信を許可 |
| モデルが動かない | オブジェクトが未登録 | **Target Object** にオブジェクトを追加 |
| 一部のキーが動かない | シェイプキー名の不一致 | シェイプキー名を ARKit 名と完全一致（大文字・小文字を区別）させる |
| 動きが途切れる | 通信遅延 | 有線 LAN または 5GHz 帯の Wi-Fi を推奨 |
| 左右が逆になる | モデルの向き | **Mirror Left/Right** を有効にする |
| 「Cannot clear while running」と表示される | 受信中 | **Stop LiveLinkFace** で停止してからクリア |

受信ログ（`[LiveLinkFace] Listening on ...` など）は Blender のシステムコンソールに出力されます。

# 🧑‍🎨 想定ユーザー

* フェイシャルリグ・シェイプキーを作成するアーティスト
* Blender で表情アニメーションを検証したい方
* Perfect Sync 対応モデルを開発・調整している方

# 🛠️ 開発者向け

統合テストは Blender のバックグラウンドモードで実行します。

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/test_addon.py
```

同じテストが push とプルリクエストごとに GitHub Actions 上の Blender 4.5 LTS で自動実行されます。

## リリース手順

1. `__init__.py` の `bl_info` の `version` を更新します。
1. `CHANGELOG.md` に `## YYYYMMDD-<バージョン>` のセクションを追加します。
1. Actions タブから **Release** ワークフローを手動で実行します。

ワークフローはテストを実行したあと、CHANGELOG の見出しをタグ名にしてリリースを作成します。
そのセクションをリリースノートに使い、`__init__.py` と `LICENSE` だけを含む `livelinkface_arkit_receiver-<バージョン>.zip` を添付します。

# ⚖️ ライセンス

このアドオンは GNU General Public License v3 (GPL-3.0) のもとで公開されています。
自由に改変・再配布が可能ですが、同様のライセンスを継承してください。

# 🙏 作者より

本アドオンは「アーティストが自分の表情で作品を動かす喜び」を支援する目的で作成しました。
もし改善点や不具合を見つけた場合は、ぜひ [Discussions](https://github.com/shun126/livelinkface_arkit_receiver/discussions) または [Issues](https://github.com/shun126/livelinkface_arkit_receiver/issues) からお知らせください。

* Shun Moriya ([X.com](https://x.com/monjiro1972))
* のんびり ([X.com](https://x.com/happy_game_dev) / [YouTube](https://www.youtube.com/channel/UCkLXe57GpUyaOoj2ycREU1Q))

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/M4M413XDXB)

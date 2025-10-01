<div align="center">
<h1>LiveLinkFace ARKit Receiver for Blender</h1>
</div>

[![license](https://img.shields.io/github/license/shun126/livelinkface_arkit_receiver)](https://github.com/shun126/livelinkface_arkit_receiver/blob/main/LICENSE)
[![release](https://img.shields.io/github/v/release/shun126/livelinkface_arkit_receiver)](https://github.com/shun126/livelinkface_arkit_receiver/releases)
[![downloads](https://img.shields.io/github/downloads/shun126/livelinkface_arkit_receiver/total)](https://github.com/shun126/livelinkface_arkit_receiver/releases)
[![stars](https://img.shields.io/github/stars/shun126/livelinkface_arkit_receiver?style=social)](https://github.com/shun126/livelinkface_arkit_receiver/stargazers)

![livelinkface_arkit_receiver](https://github.com/shun126/livelinkface_arkit_receiver/wiki/livelinkface_arkit_receiver.gif)

**LiveLinkFace ARKit Receiver** は、iPhone の **Live Link Face** アプリから送信されるフェイシャルトラッキングデータを **Blender** に受信し、シェイプキーへ自動的に適用するアドオンです。

> 🎨 アーティストが「自分の顔でモデルを動かす」ためのシンプルなツールです。

# 🚀 主な特徴

- 📱 **iPhone Live Link Face（ARKitモード）専用**
- 🧠 **リアルタイムプレビュー** に対応（受信中のシェイプキー値をHUD表示）
- 🪞 **Perfect Sync対応モデルの検証** に最適
- ⚙️ Blender **4.5** で開発・動作確認済み
- ❌ Metahumanプロトコル非対応（ARKitのみ）

# 🧩 インストール方法

1. このリポジトリをダウンロードまたはクローンします：
   ```bash
   git clone https://github.com/shun126/livelinkface_arkit_receiver.git
   ```
1. Blenderを開き、 `編集 > プリファレンス > アドオン > インストール...` を選択。
1. ダウンロードした .zip ファイルを選択し、インストールします。
1. 「LiveLinkFace ARKit Receiver」にチェックを入れて有効化します。

# 📡 使用方法
## 1. iPhone側の設定

* 「Live Link Face」アプリを起動します。
* 設定画面で IPアドレス に Blender 実行PCのローカルIPを入力。 例：`192.168.0.10`
* ポート番号 はデフォルト（`11111`）を使用します。

## 2. Blender側の設定

* LiveLinkFace パネルを開きます
* Live Link Faceと同期するシェイプキーを含んだモデルを指定します
* Start LiveLinkFace をクリック。
* モデルに対応する Shape Key 名 が自動で検出されます。

表情を動かすと、Blender上のモデルにもリアルタイムで反映されます。

# 🧰 シェイプキー対応（ARKit 52キー）

このアドオンは Apple ARKit の 52 シェイプキー名を使用します。
モデルが Perfect Sync 対応であれば、そのまま動作します。

|Shape Key|説明|
|--|--|
|browInnerUp|眉を上げる|
|jawOpen|口を開く|
|eyeBlinkLeft|左目まばたき|
|mouthSmileRight|右スマイル|

（→ 完全リストは https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation を参照して下さい）

# 💡 トラブルシューティング

| 症状         | 原因             | 対処法                  |
| ---------- | -------------- | -------------------- |
| モデルが動かない   | IP設定が異なる       | iPhoneとPCが同じWi-Fiか確認 |
| 値が途切れる     | 通信遅延           | 有線LANまたは5GHz帯を推奨     |
| 一部のキーが動かない | Shape Key名の不一致 | Blender側のキー名を確認      |

# 🧑‍🎨 想定ユーザー

* フェイシャルリグ・シェイプキーを作成するアーティスト
* Blenderで表情アニメーションを検証したい方
* Perfect Sync対応モデルを開発・調整している方

# ⚖️ ライセンス

このアドオンは GNU General Public License v3 (GPL-3.0) のもとで公開されています。
自由に改変・再配布が可能ですが、同様のライセンスを継承してください。

# 🙏 作者より

本アドオンは「アーティストが自分の表情で作品を動かす喜び」を支援する目的で作成しました。
もし改善点や不具合を見つけた場合は、ぜひ [Discussions](https://github.com/shun126/livelinkface_arkit_receiver/discussions) または [Issues](https://github.com/shun126/livelinkface_arkit_receiver/issues) からお知らせください。

* Shun Moriya ([X.com](https://x.com/monjiro1972))
* のんびり ([X.com](https://x.com/happy_game_dev) / [YouTube](https://www.youtube.com/channel/UCkLXe57GpUyaOoj2ycREU1Q))

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/M4M413XDXB)

<div align="center">
<h1>LiveLinkFace ARKit Receiver for Blender</h1>

English | [日本語](README.ja.md)
</div>

[![license](https://img.shields.io/github/license/shun126/livelinkface_arkit_receiver)](https://github.com/shun126/livelinkface_arkit_receiver/blob/main/LICENSE)
[![release](https://img.shields.io/github/v/release/shun126/livelinkface_arkit_receiver)](https://github.com/shun126/livelinkface_arkit_receiver/releases)
[![downloads](https://img.shields.io/github/downloads/shun126/livelinkface_arkit_receiver/total)](https://github.com/shun126/livelinkface_arkit_receiver/releases)
[![stars](https://img.shields.io/github/stars/shun126/livelinkface_arkit_receiver?style=social)](https://github.com/shun126/livelinkface_arkit_receiver/stargazers)
[![Blender Add-on Tests](https://github.com/shun126/livelinkface_arkit_receiver/actions/workflows/blender-tests.yml/badge.svg)](https://github.com/shun126/livelinkface_arkit_receiver/actions/workflows/blender-tests.yml)

![livelinkface_arkit_receiver](https://github.com/shun126/livelinkface_arkit_receiver/wiki/livelinkface_arkit_receiver.gif)

**LiveLinkFace ARKit Receiver** is a Blender add-on that receives facial tracking data from the iPhone **Live Link Face** app and applies it to your model's shape keys in real time.

> 🎨 A simple tool for artists who want to drive their models with their own face.

# 🚀 Features

- Receives **ARKit blendshapes** from iPhone Live Link Face over UDP
- Applies values to shape keys in **real time** (about 60 updates per second)
- Drives **multiple target objects** at once (e.g. face, eyelashes, teeth)
- **Mirror Left/Right** option to swap left and right blendshape values
- **Clear Shape Key Values** button to reset all ARKit shape keys to 0
- Great for testing **Perfect Sync** compatible models
- Developed and tested with Blender **4.5**
- ARKit protocol only (MetaHuman Animator mode, head rotation and eye rotation are not supported)

# 🧩 Installation

1. Download `livelinkface_arkit_receiver-<version>.zip` from the [Releases](https://github.com/shun126/livelinkface_arkit_receiver/releases) page.
1. Open Blender and drag and drop the downloaded .zip file into the Blender window.
   (Alternatively, use **Edit > Preferences > Add-ons > Install from Disk...**)
1. Make sure **LiveLinkFace ARKit Receiver** is enabled.

# 📡 Usage

## 1. Set up the iPhone

* Connect your iPhone and PC to the same network.
* Launch the **Live Link Face** app and select the **Live Link (ARKit)** mode.
* In the app's Live Link settings, add a target:
  * **IP address**: the local IP address of the PC running Blender (e.g. `192.168.0.10`)
  * **Port**: `11111` (default)

## 2. Set up Blender

1. In the 3D Viewport, open the Sidebar (`N` key) and select the **LiveLinkFace** tab.
1. Check **IP** and **Port**.
   * **IP**: the address to listen on. `0.0.0.0` (all interfaces) works in most cases.
   * **Port**: must match the port set in the iPhone app (default `11111`).
1. Under **Target Object**, click `+` and pick a mesh object that has ARKit-named shape keys.
   Add as many objects as you need; remove the selected one with `-`.
1. Click **Start LiveLinkFace**.

Move your face and the model in Blender follows in real time.
Click **Stop LiveLinkFace** to stop receiving.

## Panel options

| Option | Description |
| --- | --- |
| IP / Port | Address and UDP port to listen on |
| Target Object | List of objects whose shape keys are driven |
| Clear Shape Key Values | Resets all ARKit shape keys of the target objects to 0. If the list is empty, the active object is used. Only available while stopped. |
| Start / Stop LiveLinkFace | Starts or stops receiving data |
| Mirror Left/Right | Swaps left and right blendshape values (e.g. `eyeBlinkLeft` ⇔ `eyeBlinkRight`). Can be toggled while running. |

# 🧰 Shape Keys (ARKit 52 blendshapes)

The add-on drives shape keys whose names **exactly match** the 52 Apple ARKit blendshape names (case-sensitive).
Shape keys with other names are left untouched, so a Perfect Sync compatible model works out of the box.

| Group | Shape key names |
| --- | --- |
| Eyes (left) | `eyeBlinkLeft` `eyeLookDownLeft` `eyeLookInLeft` `eyeLookOutLeft` `eyeLookUpLeft` `eyeSquintLeft` `eyeWideLeft` |
| Eyes (right) | `eyeBlinkRight` `eyeLookDownRight` `eyeLookInRight` `eyeLookOutRight` `eyeLookUpRight` `eyeSquintRight` `eyeWideRight` |
| Jaw | `jawForward` `jawLeft` `jawRight` `jawOpen` |
| Mouth | `mouthClose` `mouthFunnel` `mouthPucker` `mouthLeft` `mouthRight` `mouthSmileLeft` `mouthSmileRight` `mouthFrownLeft` `mouthFrownRight` `mouthDimpleLeft` `mouthDimpleRight` `mouthStretchLeft` `mouthStretchRight` `mouthRollLower` `mouthRollUpper` `mouthShrugLower` `mouthShrugUpper` `mouthPressLeft` `mouthPressRight` `mouthLowerDownLeft` `mouthLowerDownRight` `mouthUpperUpLeft` `mouthUpperUpRight` |
| Brows | `browDownLeft` `browDownRight` `browInnerUp` `browOuterUpLeft` `browOuterUpRight` |
| Cheeks | `cheekPuff` `cheekSquintLeft` `cheekSquintRight` |
| Nose | `noseSneerLeft` `noseSneerRight` |
| Tongue | `tongueOut` |

For details on each blendshape, see [Apple's ARKit documentation](https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation).

# 💡 Troubleshooting

| Symptom | Possible cause | Solution |
| --- | --- | --- |
| The model does not move | Wrong IP address / different network | Check the IP address set in the iPhone app and make sure the iPhone and PC are on the same network |
| The model does not move | Blocked by firewall | Allow incoming UDP on the port (default `11111`) for Blender |
| The model does not move | Object not in the list | Add the object under **Target Object** |
| Some shape keys do not move | Shape key name mismatch | Rename the shape keys to the exact ARKit names (case-sensitive) |
| Motion is choppy | Network latency | Use a wired LAN or 5 GHz Wi-Fi |
| Left and right are reversed | Model orientation | Enable **Mirror Left/Right** |
| "Cannot clear while running" | Receiver is running | Click **Stop LiveLinkFace** first, then clear |

Receiver logs (such as `[LiveLinkFace] Listening on ...`) are printed to Blender's system console.

# 🧑‍🎨 Who is this for?

* Artists creating facial rigs and shape keys
* Anyone who wants to test facial animation in Blender
* Creators developing or tuning Perfect Sync compatible models

# 🛠️ Development

Integration tests run inside Blender in background mode:

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/test_addon.py
```

The same tests run automatically on GitHub Actions against Blender 4.5 LTS for every push and pull request.

## Releasing

1. Bump `version` in `bl_info` in `__init__.py`.
1. Add a `## YYYYMMDD-<version>` section to `CHANGELOG.md`.
1. Run the **Release** workflow manually from the Actions tab.

The workflow runs the tests, then creates a release tagged with the CHANGELOG heading.
It uses that section as the release notes and attaches `livelinkface_arkit_receiver-<version>.zip`, which contains only `__init__.py` and `LICENSE`.

# ⚖️ License

This add-on is released under the GNU General Public License v3 (GPL-3.0).
You are free to modify and redistribute it, as long as derivative works are distributed under the same license.

# 🙏 From the authors

We made this add-on to share the joy of bringing your artwork to life with your own expressions.
If you find a bug or have an idea for improvement, please let us know via [Discussions](https://github.com/shun126/livelinkface_arkit_receiver/discussions) or [Issues](https://github.com/shun126/livelinkface_arkit_receiver/issues).

* Shun Moriya ([X.com](https://x.com/monjiro1972))
* Nonbiri ([X.com](https://x.com/happy_game_dev) / [YouTube](https://www.youtube.com/channel/UCkLXe57GpUyaOoj2ycREU1Q))

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/M4M413XDXB)

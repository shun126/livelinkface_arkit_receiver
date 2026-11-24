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

**LiveLinkFace ARKit Receiver** is a Blender add-on that receives facial tracking data from the iPhone **Live Link Face** app and applies it to your model's shape keys and bones in real time.

> 🎨 A simple tool for artists who want to drive their models with their own face.

# 🚀 Features

- Receives **ARKit blendshapes** from iPhone Live Link Face over UDP
- Applies values to shape keys in **real time** (about 60 updates per second)
- Drives **multiple target objects** at once (e.g. face, eyelashes, teeth)
- **Mirror Left/Right** option to swap left and right blendshape values
- **Clear Shape Key Values** button to reset all ARKit shape keys to 0
- Drives **eye, neck and head bones** from the received rotation
- Writes head and eye rotation to **custom properties** for use with drivers
- **Timelapse recording** and tools to record, clear and clean up facial keys
- Great for testing **Perfect Sync** compatible models
- Supports Blender **4.5** and **5.1**
- ARKit protocol only (MetaHuman Animator mode is not supported)

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

## 3. Set up bones (eyes, neck, head)

Expand the **Bones** section of the LiveLinkFace panel.

1. Set **Armature** to the armature you want to drive.
1. Enable **Drive Eye Bones** and/or **Drive Neck/Head Bones** (both are off by default).
1. Pick the bones. If the neck is empty, the head bone receives the full head rotation.
1. Use **Neck Weight** to set the neck's share of the rotation (default 0.4, leaving 0.6 for the head).
1. If the motion is too large or too small, adjust **Eye Scale** / **Head Scale**.

The bone's `rotation_mode` is never changed, so Quaternion, Euler and Axis Angle rigs all work.

### Axis mapping

A Blender bone's local Y axis points along the bone, so the correct axes depend on the bone's direction.
For each of Pitch, Yaw and Roll you can choose a local axis (X / Y / Z) and invert its sign.

| Bones | Pitch | Yaw | Roll | Expected bone direction |
| --- | --- | --- | --- | --- |
| Eyes | X | Z | Y | Forward |
| Neck / Head | X | Y | Z | Up |

If a bone turns the wrong way, invert that channel. If it turns around the wrong axis, change the axis.

### Custom properties (for drivers)

With **Write Custom Properties** enabled, these 9 custom properties are written to the target objects.
Unlike shape keys, they keep negative values, so they can be used as driver inputs.

`headYaw` `headPitch` `headRoll` `leftEyeYaw` `leftEyePitch` `leftEyeRoll` `rightEyeYaw` `rightEyePitch` `rightEyeRoll`

The values are the received values. Mirror is applied, but Scale is not.

## Panel options

| Option | Description |
| --- | --- |
| IP / Port | Address and UDP port to listen on |
| Target Object | List of objects whose shape keys are driven |
| Clear Shape Key Values | Resets all ARKit shape keys of the target objects to 0. If the list is empty, the active object is used. Only available while stopped. |
| Start / Stop LiveLinkFace | Starts or stops receiving data |
| Mirror Left/Right | Swaps left and right blendshape values (e.g. `eyeBlinkLeft` ⇔ `eyeBlinkRight`). Also applies to head and eye rotation. Can be toggled while running. |
| Timelapse (header checkbox) / Interval | Inserts keys at the set frame interval while receiving. The checkbox stays visible when the group is collapsed. |
| Record Facial Pose | Inserts keys on the current frame for values that changed since the previous key |
| Clear Facial Animation Keys | Deletes shape key and enabled bone keys on the current frame |
| Clear ALL Facial Keys | Deletes all shape key and enabled bone keys |
| Cleanup Facial Animation Keys | Removes redundant keys whose value barely changes |
| Bones | Armature, bones, distribution, scale, axis mapping and custom properties |

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
| A bone turns the wrong way | Axis mapping does not match the bone | Change the axis or invert it in the **Bones** section |
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

The same tests run automatically on GitHub Actions against Blender 4.5 LTS and 5.2 LTS for pull requests and pushes to `main`.

## Releasing

1. Bump `version` in `bl_info` in `__init__.py`.
1. Add a `## YYYYMMDD-<version>` section to `CHANGELOG.md`.
1. Push a tag whose name exactly matches that heading:

   ```sh
   git tag YYYYMMDD-<version>
   git push origin YYYYMMDD-<version>
   ```

The **Release** workflow runs the tests, then creates a release for the tag. It fails if the tag does not match the CHANGELOG heading for the `bl_info` version.
It uses that section as the release notes and attaches `livelinkface_arkit_receiver-<version>.zip`, which contains `__init__.py`, `CHANGELOG.md` and `LICENSE`.

# ⚖️ License

This add-on is released under the GNU General Public License v3 (GPL-3.0).
You are free to modify and redistribute it, as long as derivative works are distributed under the same license.

# 🙏 From the authors

We made this add-on to share the joy of bringing your artwork to life with your own expressions.
If you find a bug or have an idea for improvement, please let us know via [Discussions](https://github.com/shun126/livelinkface_arkit_receiver/discussions) or [Issues](https://github.com/shun126/livelinkface_arkit_receiver/issues).

* Shun Moriya ([X.com](https://x.com/monjiro1972))
* Nonbiri ([X.com](https://x.com/happy_game_dev) / [YouTube](https://www.youtube.com/channel/UCkLXe57GpUyaOoj2ycREU1Q))

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/M4M413XDXB)

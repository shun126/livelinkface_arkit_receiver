bl_info = {
    "name": "LiveLinkFace ARKit Receiver",
    "author": "Shun Moriya",
    "version": (0, 5),
    "blender": (4, 5, 0),
    "location": "View3D sidebar > LiveLinkFace",
    "description": "Receive ARKit blendshapes and head/eye rotation via UDP and drive shapekeys and bones in real-time",
    "category": "Animation",
    "doc_url": "https://github.com/shun126/livelinkface_arkit_receiver",
}

import bpy
import threading
import socket
import struct
from bpy.props import EnumProperty, IntProperty, BoolProperty, FloatProperty, StringProperty, PointerProperty, CollectionProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras import anim_utils
from mathutils import Euler
from typing import NamedTuple

# ARKitの一般的な名前 - ユーザーは自分のシェイプキーをこれらの名前にマッピングすることができます。
ARKit_BLENDSHAPES = [
    # Left eye blend shapes
    "eyeBlinkLeft",
    "eyeLookDownLeft",
    "eyeLookInLeft",
    "eyeLookOutLeft",
    "eyeLookUpLeft",
    "eyeSquintLeft",
    "eyeWideLeft",
    # Right eye blend shapes
    "eyeBlinkRight",
    "eyeLookDownRight",
    "eyeLookInRight",
    "eyeLookOutRight",
    "eyeLookUpRight",
    "eyeSquintRight",
    "eyeWideRight",
    # Jaw blend shapes
    "jawForward",
    "jawLeft",
    "jawRight",
    "jawOpen",
    # Mouth blend shapes
    "mouthClose",
    "mouthFunnel",
    "mouthPucker",
    "mouthLeft",
    "mouthRight",
    "mouthSmileLeft",
    "mouthSmileRight",
    "mouthFrownLeft",
    "mouthFrownRight",
    "mouthDimpleLeft",
    "mouthDimpleRight",
    "mouthStretchLeft",
    "mouthStretchRight",
    "mouthRollLower",
    "mouthRollUpper",
    "mouthShrugLower",
    "mouthShrugUpper",
    "mouthPressLeft",
    "mouthPressRight",
    "mouthLowerDownLeft",
    "mouthLowerDownRight",
    "mouthUpperUpLeft",
    "mouthUpperUpRight",
    # Brow blend shapes
    "browDownLeft",
    "browDownRight",
    "browInnerUp",
    "browOuterUpLeft",
    "browOuterUpRight",
    # Cheek blend shapes
    "cheekPuff",
    "cheekSquintLeft",
    "cheekSquintRight",
    # Nose blend shapes
    "noseSneerLeft",
    "noseSneerRight",
    "tongueOut",
    # Treat the head rotation as curves for LiveLink support
    #"headYaw",
    #"headPitch",
    #"headRoll",
    # Treat eye rotation as curves for LiveLink support
    #"leftEyeYaw",
    #"leftEyePitch",
    #"leftEyeRoll",
    #"rightEyeYaw",
    #"rightEyePitch",
    #"rightEyeRoll",
]


# 受信 float 配列のうち、ブレンドシェイプ（0–51）に続く回転値の位置
HEAD_YAW, HEAD_PITCH, HEAD_ROLL = 52, 53, 54
L_EYE_YAW, L_EYE_PITCH, L_EYE_ROLL = 55, 56, 57
R_EYE_YAW, R_EYE_PITCH, R_EYE_ROLL = 58, 59, 60
LIVELINK_VALUE_COUNT = 61

CUSTOM_PROPERTY_INDICES = (
    ("headYaw", HEAD_YAW),
    ("headPitch", HEAD_PITCH),
    ("headRoll", HEAD_ROLL),
    ("leftEyeYaw", L_EYE_YAW),
    ("leftEyePitch", L_EYE_PITCH),
    ("leftEyeRoll", L_EYE_ROLL),
    ("rightEyeYaw", R_EYE_YAW),
    ("rightEyePitch", R_EYE_PITCH),
    ("rightEyeRoll", R_EYE_ROLL),
)

AXIS_INDEX = {'X': 0, 'Y': 1, 'Z': 2}
AXIS_ITEMS = (
    ('X', "X", "Local X axis"),
    ('Y', "Y", "Local Y axis (along the bone)"),
    ('Z', "Z", "Local Z axis"),
)
OBJECT_TYPE_ICONS = {
    'MESH': 'OUTLINER_OB_MESH',
    'ARMATURE': 'OUTLINER_OB_ARMATURE',
}

def axis_enum_property(name, default):
    return EnumProperty(name=name, items=AXIS_ITEMS, default=default)

def armature_object_poll(self, obj):
    return obj.type == 'ARMATURE'

class LeftRightBlendshapeIdxs(NamedTuple):
    Left: int
    Right: int
    
MIRRORABLE_BLENDSHAPE_PAIRS = []

for i, blendshape in enumerate(ARKit_BLENDSHAPES):
    if blendshape[-4:] == "Left":
        left_idx = i
        try:
            right_idx = ARKit_BLENDSHAPES.index(blendshape[:-4] + "Right")
        except ValueError:
            continue
        MIRRORABLE_BLENDSHAPE_PAIRS.append(LeftRightBlendshapeIdxs(left_idx, right_idx))

receiver_thread_stop_event = threading.Event()
receiver_thread_handle = None
shared_values = None
shared_values_lock = threading.Lock()

# ---------------------------
# レシーバースレッド
# ---------------------------
class receiver_thread(threading.Thread):
    def __init__(self, ip, port, stop_event):
        super().__init__(daemon=True)
        self.ip = ip
        self.port = port
        self.stop_event = stop_event
        self.sock = None

    def run(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.ip, self.port))
            self.sock.settimeout(0.5)
            print(f"[LiveLinkFace] Listening on {self.ip}:{self.port}")
            while not self.stop_event.is_set():
                try:
                    data, _ = self.sock.recvfrom(65536)
                    #print(f"Received packet size={len(data)} bytes")
                    # 16進ダンプに変換
                    #print(" ".join(f"{b:02X}" for b in data))

                    # https://github.com/aelzeiny/Animoji/blob/main/livelink.py
                    #if version != 6:
                    #    raise NotImplementedError("Cannot support packet version: " + str(version))
                    offset = 0

                    # 先頭4バイト = メッセージタイプ
                    msg_type = struct.unpack_from(">b", data, offset)[0]
                    offset += 1

                    uuid_length = struct.unpack_from(">i", data, offset)[0]
                    offset += 4

                    # UUID (36文字)
                    uuid = data[offset:offset+36].decode("utf-8")
                    offset += 36

                    # デバイス名の長さ
                    device_name_length = struct.unpack_from(">i", data, offset)[0]
                    offset += 4

                    # デバイス名
                    device_name = data[offset:offset+device_name_length].decode("utf-8")
                    offset += device_name_length
                    offset += 1

                    #frametime = struct.unpack_from('>ifii', data, offset)
                    #offset += struct.calcsize('>ifii')
                    offset += 4
                    offset += 4
                    offset += 4
                    offset += 4

                    print(f"Message type: {msg_type}, UUID: {uuid}, Device: {device_name} ({device_name_length})")

                    # 残りは float 配列
                    values = struct.unpack_from(">" + "f" * ((len(data)-offset)//4), data, offset)
                    #for i, v in enumerate(values):
                    #    print(f"{i:03}: {v}")
                    #values = struct.unpack("<" + "f" * 52, data[:52*4])
                    #print(values)bpy.app.timers.register(lambda: apply_blendshapes(target_obj, values), first_interval=0.0)

                    with shared_values_lock:
                        global shared_values
                        shared_values = values

                except socket.timeout:
                    continue
                except Exception as e:
                    print("recv error:", e)
                    continue
        except Exception as e:
            print("receiver setup error:", e)
        finally:
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            print("[LiveLinkFace] Receiver thread exiting")

def apply_blendshapes(target_obj, values):
    for i, key in enumerate(ARKit_BLENDSHAPES):
        if key in target_obj.data.shape_keys.key_blocks:
            target_obj.data.shape_keys.key_blocks[key].value = values[i]
            #print(f"Set {key} to {values[i]}")

def get_shape_keys(obj):
    """シェイプキーを持たないオブジェクト（アーマチュア等）では None を返す"""
    return getattr(obj.data, "shape_keys", None) if obj else None

def get_axis_map(props, prefix):
    return {
        channel: (
            getattr(props, f"{prefix}_{channel}_axis"),
            getattr(props, f"{prefix}_{channel}_invert"),
        )
        for channel in ("pitch", "yaw", "roll")
    }

def set_bone_rotation(pose_bone, pitch, yaw, roll, axis_map, scale=1.0):
    """回転を合成し、骨の rotation_mode を変えずに書き込む"""
    angles = [0.0, 0.0, 0.0]
    for channel, value in (("pitch", pitch), ("yaw", yaw), ("roll", roll)):
        axis, invert = axis_map[channel]
        angles[AXIS_INDEX[axis]] += (-value if invert else value) * scale

    rotation = Euler(angles, 'XYZ').to_quaternion()
    mode = pose_bone.rotation_mode
    if mode == 'QUATERNION':
        # 補間時に遠回りしないよう、現在の姿勢と符号を揃える
        rotation.make_compatible(pose_bone.rotation_quaternion)
        pose_bone.rotation_quaternion = rotation
    elif mode == 'AXIS_ANGLE':
        axis, angle = rotation.to_axis_angle()
        pose_bone.rotation_axis_angle = (angle, axis.x, axis.y, axis.z)
    else:
        pose_bone.rotation_euler = rotation.to_euler(mode, pose_bone.rotation_euler)

def apply_bones(arm_obj, values, props):
    """目・首・頭の骨へ回転を適用し、書き込みがあれば True を返す"""
    if len(values) < LIVELINK_VALUE_COUNT or not arm_obj.pose:
        return False

    bones = arm_obj.pose.bones
    applied = False

    if props.apply_eye_bones:
        axis_map = get_axis_map(props, "eye")
        for name, yaw_idx, pitch_idx, roll_idx in (
            (props.eye_bone_left, L_EYE_YAW, L_EYE_PITCH, L_EYE_ROLL),
            (props.eye_bone_right, R_EYE_YAW, R_EYE_PITCH, R_EYE_ROLL),
        ):
            bone = bones.get(name) if name else None
            if bone:
                set_bone_rotation(
                    bone, values[pitch_idx], values[yaw_idx], values[roll_idx],
                    axis_map, props.eye_scale,
                )
                applied = True

    if props.apply_head_bones:
        axis_map = get_axis_map(props, "head")
        neck = bones.get(props.neck_bone) if props.neck_bone else None
        head = bones.get(props.head_bone) if props.head_bone else None
        # 片方しか無い場合は、回転を失わないよう残った骨に全量を配分する
        neck_share = props.neck_weight if neck and head else 1.0
        head_share = 1.0 - props.neck_weight if neck and head else 1.0
        for bone, share in ((neck, neck_share), (head, head_share)):
            if bone:
                set_bone_rotation(
                    bone, values[HEAD_PITCH], values[HEAD_YAW], values[HEAD_ROLL],
                    axis_map, props.head_scale * share,
                )
                applied = True

    return applied

def write_custom_properties(obj, values):
    if len(values) < LIVELINK_VALUE_COUNT:
        return False
    for name, index in CUSTOM_PROPERTY_INDICES:
        obj[name] = float(values[index])
    return True

def mirror_values(values):
    """左右を入れ替えた値のリストを返す"""
    mirrored = list(values)
    for pair in MIRRORABLE_BLENDSHAPE_PAIRS:
        mirrored[pair.Left], mirrored[pair.Right] = mirrored[pair.Right], mirrored[pair.Left]

    if len(mirrored) >= LIVELINK_VALUE_COUNT:
        mirrored[HEAD_YAW] = -values[HEAD_YAW]
        mirrored[HEAD_ROLL] = -values[HEAD_ROLL]
        mirrored[L_EYE_YAW] = -values[R_EYE_YAW]
        mirrored[L_EYE_PITCH] = values[R_EYE_PITCH]
        mirrored[L_EYE_ROLL] = -values[R_EYE_ROLL]
        mirrored[R_EYE_YAW] = -values[L_EYE_YAW]
        mirrored[R_EYE_PITCH] = values[L_EYE_PITCH]
        mirrored[R_EYE_ROLL] = -values[L_EYE_ROLL]
    return mirrored

def unique_objects(objects):
    result = []
    for obj in objects:
        if obj and obj not in result:
            result.append(obj)
    return result

def get_target_objects(props):
    """ターゲット一覧とアーマチュア指定を、重複なしで返す"""
    return unique_objects(
        [item.target_object for item in props.target_objects] + [props.armature_object]
    )

def get_target_armatures(props):
    return [obj for obj in get_target_objects(props) if obj.type == 'ARMATURE']

def get_key_targets(context, props):
    return get_target_objects(props) or unique_objects([getattr(context, "object", None)])

# ---------------------------
# キーフレーム
# ---------------------------
class KeyChannel(NamedTuple):
    id_data: object     # FCurve を持つ ID（Object または Key）
    owner: object       # PoseBone または ShapeKey
    prop: str
    index: int          # 配列プロパティの要素番号。スカラーは -1
    data_path: str
    group: str

def get_fcurves(id_data):
    """layered Action の現在のスロットの FCurve コレクションを返す"""
    anim_data = id_data.animation_data if id_data else None
    if not anim_data or not anim_data.action or not anim_data.action_slot:
        return None
    channelbag = anim_utils.action_get_channelbag_for_slot(anim_data.action, anim_data.action_slot)
    return channelbag.fcurves if channelbag else None

def find_channel_fcurve(channel):
    fcurves = get_fcurves(channel.id_data)
    if fcurves is None:
        return None
    return fcurves.find(channel.data_path, index=max(channel.index, 0))

def get_bone_rotation_property(pose_bone):
    mode = pose_bone.rotation_mode
    if mode == 'QUATERNION':
        return "rotation_quaternion"
    if mode == 'AXIS_ANGLE':
        return "rotation_axis_angle"
    return "rotation_euler"

def get_driven_pose_bones(arm_obj, props):
    names = []
    if props.apply_eye_bones:
        names += [props.eye_bone_left, props.eye_bone_right]
    if props.apply_head_bones:
        names += [props.neck_bone, props.head_bone]

    bones = arm_obj.pose.bones
    return [bones[name] for name in dict.fromkeys(names) if name and name in bones]

def iter_key_channels(obj, props):
    """オブジェクトのキー対象を、FCurve 1 本ごとに列挙する"""
    shape_keys = get_shape_keys(obj)
    if shape_keys:
        for key_name in ARKit_BLENDSHAPES:
            key_block = shape_keys.key_blocks.get(key_name)
            if key_block:
                yield KeyChannel(shape_keys, key_block, "value", -1, key_block.path_from_id("value"), "")

    if obj and obj.type == 'ARMATURE' and obj.pose:
        for bone in get_driven_pose_bones(obj, props):
            prop = get_bone_rotation_property(bone)
            data_path = bone.path_from_id(prop)
            for index in range(len(getattr(bone, prop))):
                yield KeyChannel(obj, bone, prop, index, data_path, bone.name)

def insert_channel_key(channel, frame, threshold=None):
    """キーを打つ。threshold 指定時は、前回キーとの差が threshold 以下なら打たない"""
    if threshold is not None:
        fcurve = find_channel_fcurve(channel)
        if fcurve:
            previous = None
            has_key_on_frame = False
            for point in fcurve.keyframe_points:
                if int(point.co[0]) == frame:
                    has_key_on_frame = True
                elif point.co[0] < frame:
                    previous = point.co[1]
            value = getattr(channel.owner, channel.prop)
            if channel.index >= 0:
                value = value[channel.index]
            # 現在フレームの既存キーは、古い値を残さないよう必ず更新する
            if not has_key_on_frame and previous is not None and abs(value - previous) <= threshold:
                return False

    kwargs = {"group": channel.group} if channel.group else {}
    return channel.owner.keyframe_insert(channel.prop, index=channel.index, frame=frame, **kwargs)

def cleanup_fcurve(fcurve, threshold):
    """直前に残したキーとの差が threshold 以下のキーを削除し、削除数を返す"""
    points = fcurve.keyframe_points
    redundant = []
    last_value = None
    for index, point in enumerate(points):
        value = point.co[1]
        if last_value is not None and abs(value - last_value) <= threshold:
            redundant.append(index)
        else:
            last_value = value

    # 削除で要素がずれないよう後ろから消す
    for index in reversed(redundant):
        points.remove(points[index], fast=True)
    if redundant:
        fcurve.update()
    return len(redundant)

def tag_animation_editors(context):
    screen = context.screen
    if not screen:
        return
    for area in screen.areas:
        if area.type in {'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
            area.tag_redraw()

def process_queue():
    props = bpy.context.scene.livelinkface_props

    # gather target objects
    target_objs = get_target_objects(props)

    # copy shared values under lock
    copied_shared_values = None
    with shared_values_lock:
        copied_shared_values = list(shared_values) if shared_values else None

    if copied_shared_values:
        # mirror left/right values if enabled
        if props.mirror:
            copied_shared_values = mirror_values(copied_shared_values)

        # apply to all target objects
        for obj in target_objs:
            updated = False
            if obj.type == 'MESH' and obj.data and obj.data.shape_keys:
                apply_blendshapes(obj, copied_shared_values)
            elif obj.type == 'ARMATURE':
                updated = apply_bones(obj, copied_shared_values, props)

            if props.write_custom_props:
                updated = write_custom_properties(obj, copied_shared_values) or updated

            if updated:
                obj.update_tag()

    # Time-lapse recording mode
    if props.timelapse_enabled:
        props.timelapse_counter += 1

        if props.timelapse_counter >= props.timelapse_interval:
            props.timelapse_counter = 0

            # Insert key into current frame
            scene = bpy.context.scene
            current_frame = scene.frame_current

            for obj in target_objs:
                for channel in iter_key_channels(obj, props):
                    insert_channel_key(channel, current_frame)

            # Advance the frames (to create a time-lapse video)
            scene.frame_set(current_frame + props.timelapse_interval)

    # keep timer running if running
    if bpy.context.scene.livelinkface_props.running:
        return 1.0 / 60.0
    else:
        return None

def clear_blendshapes(target_obj):
    shape_keys = get_shape_keys(target_obj)
    if shape_keys:
        for key in ARKit_BLENDSHAPES:
            if key in shape_keys.key_blocks:
                shape_keys.key_blocks[key].value = 0.0

# ---------------------------
# ストレージ＆マッピング
# ---------------------------
class LFObjectItem(PropertyGroup):
    target_object: PointerProperty(
        name="Target Object",
        type=bpy.types.Object,
        description="Name of object that has shapekeys"
    )

class LFO_UL_object_list(bpy.types.UIList):
    """UI list to display target objects"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        obj = item.target_object
        object_icon = OBJECT_TYPE_ICONS.get(obj.type, 'OBJECT_DATA') if obj else 'OBJECT_DATA'
        layout.prop(item, "target_object", text="", emboss=True, icon=object_icon)

class LFO_OT_add_object(bpy.types.Operator):
    bl_idname = "livelinkface.add_object"
    bl_label = "Add Target Object"

    def execute(self, context):
        props = context.scene.livelinkface_props
        new_item = props.target_objects.add()
        new_item.name = ""
        props.active_index = len(props.target_objects) - 1
        return {'FINISHED'}

class LFO_OT_remove_object(bpy.types.Operator):
    bl_idname = "livelinkface.remove_object"
    bl_label = "Remove Target Object"

    def execute(self, context):
        props = context.scene.livelinkface_props
        if props.active_index >= 0 and props.active_index < len(props.target_objects):
            props.target_objects.remove(props.active_index)
            props.active_index = min(props.active_index, len(props.target_objects) - 1)
        return {'FINISHED'}

class LFProperties(PropertyGroup):
    listen_ip: StringProperty(name="IP", default="0.0.0.0", description="IP to bind (usually 0.0.0.0)")
    listen_port: IntProperty(name="Port", default=11111, min=1024, max=65535)
    running: BoolProperty(name="Running", default=False)
    target_objects: CollectionProperty(type=LFObjectItem)
    active_index: IntProperty()
    timelapse_enabled: BoolProperty(
        name="Timelapse Recording",
        default=False,
        description="Automatically insert keyframes every interval during LiveLink streaming"
    )

    timelapse_interval: IntProperty(
        name="Interval (Frames)",
        default=10,
        min=1,
        description="Interval in frames to record facial keyframes"
    )

    timelapse_counter: IntProperty(
        name="Counter",
        default=0
    )

    eye_bone_left: StringProperty(
        name="Left Eye Bone",
        default="eye.L",
        description="Name of the left eye bone to control"
    )

    eye_bone_right: StringProperty(
        name="Right Eye Bone",
        default="eye.R",
        description="Name of the right eye bone to control"
    )

    armature_object: PointerProperty(
        name="Armature",
        type=bpy.types.Object,
        poll=armature_object_poll,
        description="Armature whose eye, neck and head bones are driven"
    )

    neck_bone: StringProperty(
        name="Neck Bone",
        default="",
        description="Name of the neck bone. When empty, the head bone receives the full rotation"
    )

    head_bone: StringProperty(
        name="Head Bone",
        default="",
        description="Name of the head bone to control"
    )

    apply_eye_bones: BoolProperty(
        name="Drive Eye Bones",
        default=False,
        description="Apply the received eye rotation to the eye bones"
    )

    apply_head_bones: BoolProperty(
        name="Drive Neck/Head Bones",
        default=False,
        description="Apply the received head rotation to the neck and head bones"
    )

    neck_weight: FloatProperty(
        name="Neck Weight",
        default=0.4,
        min=0.0,
        max=1.0,
        description="Share of the head rotation given to the neck. The head bone receives the rest"
    )

    eye_scale: FloatProperty(
        name="Eye Scale",
        default=1.0,
        description="Multiplier applied to the received eye rotation values"
    )

    head_scale: FloatProperty(
        name="Head Scale",
        default=1.0,
        description="Multiplier applied to the received head rotation values"
    )

    # 目の骨は前向きを想定した既定値
    eye_pitch_axis: axis_enum_property("Eye Pitch Axis", 'X')
    eye_yaw_axis: axis_enum_property("Eye Yaw Axis", 'Z')
    eye_roll_axis: axis_enum_property("Eye Roll Axis", 'Y')
    eye_pitch_invert: BoolProperty(name="Invert Eye Pitch", default=False)
    eye_yaw_invert: BoolProperty(name="Invert Eye Yaw", default=False)
    eye_roll_invert: BoolProperty(name="Invert Eye Roll", default=False)

    # 首・頭の骨は上向きを想定した既定値
    head_pitch_axis: axis_enum_property("Head Pitch Axis", 'X')
    head_yaw_axis: axis_enum_property("Head Yaw Axis", 'Y')
    head_roll_axis: axis_enum_property("Head Roll Axis", 'Z')
    head_pitch_invert: BoolProperty(name="Invert Head Pitch", default=False)
    head_yaw_invert: BoolProperty(name="Invert Head Yaw", default=False)
    head_roll_invert: BoolProperty(name="Invert Head Roll", default=False)

    write_custom_props: BoolProperty(
        name="Write Custom Properties",
        default=False,
        description="Write head and eye rotation to custom properties on target objects for use with drivers"
    )

    mirror: BoolProperty(
        name="Mirror Left/Right",
        description="Swap left and right ARKit blendshape values",
        default=False,
    )

# ---------------------------
# Operators / Panel
# ---------------------------
class LFO_OT_start(Operator):
    bl_idname = "livelinkface.start"
    bl_label = "Start LiveLinkFace"

    def execute(self, context):
        global receiver_thread_handle, receiver_thread_stop_event
        props = context.scene.livelinkface_props
        if props.running:
            self.report({'WARNING'}, "Already running")
            return {'CANCELLED'}
        receiver_thread_stop_event = threading.Event()
        # bind to 0.0.0.0 by default
        ip = props.listen_ip
        try:
            port = int(props.listen_port)
        except:
            port = 11111
        receiver_thread_handle = receiver_thread(ip, port, receiver_thread_stop_event)
        receiver_thread_handle.start()
        props.running = True

        # start timer
        bpy.app.timers.register(process_queue)

        self.report({'INFO'}, f"LiveLinkFace listening on {ip}:{port}")
        return {'FINISHED'}

class LFO_OT_stop(Operator):
    bl_idname = "livelinkface.stop"
    bl_label = "Stop LiveLinkFace"

    def execute(self, context):
        global receiver_thread_handle, receiver_thread_stop_event
        props = context.scene.livelinkface_props
        if not props.running:
            self.report({'WARNING'}, "Not running")
            return {'CANCELLED'}
        props.running = False
        if receiver_thread_stop_event:
            receiver_thread_stop_event.set()
        # allow thread to exit
        receiver_thread_handle = None
        self.report({'INFO'}, "Stopped LiveLinkFace")
        return {'FINISHED'}

class LFO_OT_clear_shape_keys(Operator):
    bl_idname = "livelinkface.clear_shape_keys"
    bl_label = "Clear Shape Key Values"

    def execute(self, context):
        props = context.scene.livelinkface_props
        if props.running:
            self.report({'WARNING'}, "Cannot clear while running. Please stop.")
            return {'CANCELLED'}
        props = bpy.context.scene.livelinkface_props

        target_objs = [item.target_object for item in props.target_objects if item.target_object]
        if not target_objs:
            target_objs = [getattr(bpy.context, "object", None)]

        for obj in target_objs:
            clear_blendshapes(obj)

        return {'FINISHED'}

class LFO_OT_record_frame_keys(Operator):
    bl_idname = "livelinkface.record_frame_keys"
    bl_label = "Record Facial Pose"
    bl_description = "Insert keys for shape keys and enabled bones that changed since the previous key"

    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0,
        description="Record only keys that changed more than this amount"
    )

    def execute(self, context):
        props = context.scene.livelinkface_props
        frame = context.scene.frame_current

        changed_count = 0
        for obj in get_key_targets(context, props):
            for channel in iter_key_channels(obj, props):
                if insert_channel_key(channel, frame, self.threshold):
                    changed_count += 1

        tag_animation_editors(context)
        self.report({'INFO'}, f"Recorded {changed_count} keys (threshold={self.threshold})")
        return {'FINISHED'}

class LFO_OT_clear_frame_keys(Operator):
    bl_idname = "livelinkface.clear_frame_keys"
    bl_label = "Clear Facial Animation Keys"
    bl_description = "Delete shape key and enabled bone keyframes on the current frame for all target objects"

    def execute(self, context):
        props = context.scene.livelinkface_props
        frame = context.scene.frame_current

        deleted = 0
        for obj in get_key_targets(context, props):
            for channel in iter_key_channels(obj, props):
                fcurve = find_channel_fcurve(channel)
                if not fcurve:
                    continue
                for index, point in enumerate(fcurve.keyframe_points):
                    if int(point.co[0]) == frame:
                        fcurve.keyframe_points.remove(fcurve.keyframe_points[index])
                        fcurve.update()
                        deleted += 1
                        break  # 同じフレームに複数キーを打つことは無いのでOK
                # 空の FCurve は評価時に値を 0 にしてしまうため取り除く
                if len(fcurve.keyframe_points) == 0:
                    get_fcurves(channel.id_data).remove(fcurve)

        tag_animation_editors(context)
        self.report({'INFO'}, f"Deleted {deleted} keys on frame {frame}")
        return {'FINISHED'}

class LFO_OT_clear_all_facial_keys(Operator):
    bl_idname = "livelinkface.clear_all_facial_keys"
    bl_label = "Clear ALL Facial Keys"
    bl_description = "Delete ALL keyframes for ARKit shape keys and enabled bones on all target objects"

    def execute(self, context):
        props = context.scene.livelinkface_props

        deleted = 0
        for obj in get_key_targets(context, props):
            for channel in iter_key_channels(obj, props):
                fcurve = find_channel_fcurve(channel)
                if fcurve:
                    deleted += len(fcurve.keyframe_points)
                    get_fcurves(channel.id_data).remove(fcurve)

        tag_animation_editors(context)
        self.report({'INFO'}, f"Deleted {deleted} total facial keys.")
        return {'FINISHED'}

class LFO_OT_cleanup_keys(Operator):
    bl_idname = "livelinkface.cleanup_keys"
    bl_label = "Cleanup Facial Animation Keys"
    bl_description = "Remove nearly-identical or redundant shape key and enabled bone keyframes"

    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0,
        description="If the change is below this amount, the keyframe will be removed"
    )

    def execute(self, context):
        props = context.scene.livelinkface_props

        removed = 0
        for obj in get_key_targets(context, props):
            for channel in iter_key_channels(obj, props):
                fcurve = find_channel_fcurve(channel)
                if fcurve:
                    removed += cleanup_fcurve(fcurve, self.threshold)

        tag_animation_editors(context)
        self.report({'INFO'}, f"Cleanup done: removed {removed} keys")
        return {'FINISHED'}

class LFO_PT_panel(Panel):
    bl_idname = "LFO_PT_panel"
    bl_label = "LiveLink Face"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'LiveLinkFace'

    def draw(self, context):
        layout = self.layout
        props = context.scene.livelinkface_props

        col = layout.column()
        col.prop(props, "listen_ip")
        col.prop(props, "listen_port")

        layout.label(text="Target Object:")
        row = layout.row()
        row.template_list("LFO_UL_object_list", "", props, "target_objects", props, "active_index")
        col = row.column(align=True)
        col.operator("livelinkface.add_object", icon='ADD', text="")
        col.operator("livelinkface.remove_object", icon='REMOVE', text="")

        layout.operator("livelinkface.clear_shape_keys", icon='X')
        layout.prop(props, "mirror", icon="MOD_MIRROR")

        # サブパネルは親の本体より下に描画されるため、Start の上に置ける layout.panel を使う
        header, body = layout.panel("LFO_bones", default_closed=True)
        header.label(text="Bones")
        if body:
            draw_bones_section(body, props)

        header, body = layout.panel("LFO_timelapse", default_closed=True)
        # 閉じていても記録中か分かるよう、有効フラグは見出しに置く
        header.prop(props, "timelapse_enabled", text="Timelapse")
        if body:
            body.prop(props, "timelapse_interval")
            body.separator()
            body.operator("livelinkface.record_frame_keys", icon='KEYFRAME')
            body.operator("livelinkface.clear_frame_keys", icon='X')
            body.operator("livelinkface.clear_all_facial_keys", icon='TRASH')
            body.operator("livelinkface.cleanup_keys", icon='BRUSH_DATA')

        row = layout.row()
        if not props.running:
            row.operator("livelinkface.start", icon='PLAY')
        else:
            row.operator("livelinkface.stop", icon='PAUSE')

        layout.label(text="Usage:")
        layout.label(text="1) Add target object (name)")
        layout.label(text="2) Set iPhone LiveLinkFace target to this PC:port")
        layout.label(text="3) Start and move face on iPhone")


def draw_bone_field(layout, props, prop_name, arm_obj):
    if arm_obj:
        layout.prop_search(props, prop_name, arm_obj.data, "bones")
    else:
        layout.prop(props, prop_name)


def draw_axis_mapping(layout, props, prefix):
    col = layout.column(align=True)
    for channel in ("pitch", "yaw", "roll"):
        row = col.row(align=True)
        row.label(text=channel.capitalize())
        row.prop(props, f"{prefix}_{channel}_axis", expand=True)
        row.prop(props, f"{prefix}_{channel}_invert", text="", icon='ARROW_LEFTRIGHT')


def draw_bones_section(layout, props):
    layout.prop(props, "armature_object")
    armatures = get_target_armatures(props)
    arm_obj = armatures[0] if armatures else None

    box = layout.box()
    box.prop(props, "apply_eye_bones")
    col = box.column()
    col.active = props.apply_eye_bones
    draw_bone_field(col, props, "eye_bone_left", arm_obj)
    draw_bone_field(col, props, "eye_bone_right", arm_obj)
    col.prop(props, "eye_scale")
    draw_axis_mapping(col, props, "eye")

    box = layout.box()
    box.prop(props, "apply_head_bones")
    col = box.column()
    col.active = props.apply_head_bones
    draw_bone_field(col, props, "neck_bone", arm_obj)
    draw_bone_field(col, props, "head_bone", arm_obj)
    col.prop(props, "neck_weight", slider=True)
    col.prop(props, "head_scale")
    draw_axis_mapping(col, props, "head")

    layout.prop(props, "write_custom_props")

# ---------------------------
# Registration
# ---------------------------
classes = (
    LFObjectItem,
    LFProperties,
    LFO_UL_object_list,
    LFO_OT_add_object,
    LFO_OT_remove_object,
    LFO_OT_clear_shape_keys,
    LFO_OT_start,
    LFO_OT_stop,
    LFO_PT_panel,
    LFO_OT_record_frame_keys,
    LFO_OT_clear_frame_keys,
    LFO_OT_clear_all_facial_keys,
    LFO_OT_cleanup_keys
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.livelinkface_props = PointerProperty(type=LFProperties)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    try:
        del bpy.types.Scene.livelinkface_props
    except:
        pass

if __name__ == "__main__":
    register()

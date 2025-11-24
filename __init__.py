bl_info = {
    "name": "LiveLinkFace ARKit Receiver",
    "author": "Shun Moriya",
    "version": (0, 3),
    "blender": (4, 5, 0),
    "location": "View3D sidebar > LiveLinkFace",
    "description": "Receive ARKit blendshapes via UDP and drive shapekeys in real-time",
    "category": "Animation",
    "doc_url": "https://github.com/shun126/livelinkface_arkit_receiver",
}

import bpy
import threading
import socket
import struct
from bpy.props import IntProperty, BoolProperty, FloatProperty, StringProperty, PointerProperty, CollectionProperty
from bpy.types import Operator, Panel, PropertyGroup

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

receiver_thread_stop_event = threading.Event()
receiver_thread_handle = None
shared_values = None
shared_values_lock = threading.Lock()
previous_values = {}

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

def process_queue():
    props = bpy.context.scene.livelinkface_props

    # gather target objects
    target_objs = [item.target_object for item in props.target_objects if item.target_object]

    # copy shared values under lock
    copied_shared_values = None
    with shared_values_lock:
        copied_shared_values = shared_values

    # apply to all target objects
    if copied_shared_values:
        for obj in target_objs:
            if obj and obj.data and obj.data.shape_keys:
                apply_blendshapes(obj, copied_shared_values)

    # keep timer running if running
    if bpy.context.scene.livelinkface_props.running:
        return 1.0 / 60.0
    else:
        return None

def clear_blendshapes(target_obj):
    if target_obj and target_obj.data.shape_keys:
        for i, key in enumerate(ARKit_BLENDSHAPES):
            if key in target_obj.data.shape_keys.key_blocks:
                target_obj.data.shape_keys.key_blocks[key].value = 0.0

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
        layout.prop(item, "target_object", text="", emboss=True, icon='OUTLINER_OB_ARMATURE')

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

class LFO_OT_record_pose_force(Operator):
    bl_idname = "livelinkface.record_pose_force"
    bl_label = "Record Facial Pose (Force)"

    def execute(self, context):
        # previous_values を初期化
        global previous_values
        previous_values = {}

        # Optimized版を実行
        bpy.ops.livelinkface.record_pose_optimized('INVOKE_DEFAULT')

        self.report({'INFO'}, "Forced record: all previous values reset.")
        return {'FINISHED'}

class LFO_OT_record_pose_optimized(Operator):
    bl_idname = "livelinkface.record_pose_optimized"
    bl_label = "Record Facial Pose (Optimized)"

    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0,
        description="Record only keys that changed more than this amount"
    )

    def execute(self, context):
        props = context.scene.livelinkface_props
        scene = context.scene

        target_objs = [item.target_object for item in props.target_objects if item.target_object]
        if not target_objs:
            target_objs = [getattr(context, "object", None)]

        changed_count = 0

        for obj in target_objs:
            if not (obj and obj.data and obj.data.shape_keys):
                continue

            if obj.name not in previous_values:
                previous_values[obj.name] = [-1.0] * len(ARKit_BLENDSHAPES)

            previous_value = previous_values[obj.name]

            for i, key_name in enumerate(ARKit_BLENDSHAPES):
                if key_name in obj.data.shape_keys.key_blocks:
                    kb = obj.data.shape_keys.key_blocks[key_name]
                    current = kb.value
                    last = previous_value[i]

                    # 差分チェック
                    if abs(current - last) > self.threshold:
                        kb.keyframe_insert("value", frame=scene.frame_current)
                        previous_value[i] = current
                        changed_count += 1

        self.report({'INFO'}, f"Recorded {changed_count} keys (threshold={self.threshold})")
        return {'FINISHED'}

class LFO_OT_clear_frame_keys(Operator):
    bl_idname = "livelinkface.clear_frame_keys"
    bl_label = "Clear Keys on Current Frame"
    bl_description = "Delete all shape key keyframes on the current frame for all target objects"

    def execute(self, context):
        props = context.scene.livelinkface_props
        scene = context.scene
        frame = scene.frame_current

        target_objs = [item.target_object for item in props.target_objects if item.target_object]
        if not target_objs:
            target_objs = [context.object]

        deleted = 0

        for obj in target_objs:
            if not (obj and obj.data and obj.data.shape_keys):
                continue

            for key_name in ARKit_BLENDSHAPES:
                if key_name in obj.data.shape_keys.key_blocks:
                    kb = obj.data.shape_keys.key_blocks[key_name]

                    # shape key animation data (F-Curve) を取得
                    if kb.animation_data is None:
                        continue

                    action = kb.id_data.animation_data.action
                    if not action:
                        continue

                    # シェイプキーの value に対応する FCurve を探す
                    fcurves = action.fcurves.find('key_blocks["%s"].value' % key_name)

                    if fcurves:
                        # 現在フレームのキーを削除
                        for kp in fcurves.keyframe_points:
                            if int(kp.co[0]) == frame:
                                fcurves.keyframe_points.remove(kp)
                                deleted += 1
                                break

        self.report({'INFO'}, f"Deleted {deleted} keys on frame {frame}")
        return {'FINISHED'}

class LFO_OT_cleanup_keys(Operator):
    bl_idname = "livelinkface.cleanup_keys"
    bl_label = "Cleanup Facial Animation Keys"
    bl_description = "Remove nearly-identical or redundant shape key keyframes"

    threshold: FloatProperty(
        name="Threshold",
        default=0.001,
        min=0.0,
        description="If the change is below this amount, the keyframe will be removed"
    )

    def execute(self, context):
        props = context.scene.livelinkface_props
        scene = context.scene

        target_objs = [item.target_object for item in props.target_objects if item.target_object]
        if not target_objs:
            target_objs = [context.object]

        removed = 0

        for obj in target_objs:
            if not (obj and obj.data and obj.data.shape_keys):
                continue

            for key_name in ARKit_BLENDSHAPES:
                if key_name not in obj.data.shape_keys.key_blocks:
                    continue

                kb = obj.data.shape_keys.key_blocks[key_name]
                ad = kb.id_data.animation_data
                if not ad or not ad.action:
                    continue

                action = ad.action
                fcurve = action.fcurves.find(f'key_blocks["{key_name}"].value')
                if not fcurve:
                    continue

                keyframes = fcurve.keyframe_points

                # 差分で不要キーを削除
                last_value = None
                for kp in list(keyframes):  # コピーで回す
                    frame, value = kp.co[0], kp.co[1]

                    if last_value is not None:
                        if abs(value - last_value) <= self.threshold:
                            keyframes.remove(kp)
                            removed += 1
                            continue

                    last_value = value

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
        row = layout.row()
        if not props.running:
            row.operator("livelinkface.start", icon='PLAY')
        else:
            row.operator("livelinkface.stop", icon='PAUSE')
        layout.label(text="Usage:")
        layout.label(text="1) Add target object (name)")
        layout.label(text="2) Set iPhone LiveLinkFace target to this PC:port")
        layout.label(text="3) Start and move face on iPhone")
        layout.operator("livelinkface.record_pose_force", icon='KEYFRAME')
        layout.operator("livelinkface.record_pose_optimized", icon='KEYFRAME')
        layout.operator("livelinkface.clear_frame_keys", icon='X')
        layout.operator("livelinkface.cleanup_keys", icon='BRUSH_DATA')

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
    LFO_OT_record_pose_force,
    LFO_OT_record_pose_optimized,
    LFO_OT_clear_frame_keys,
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

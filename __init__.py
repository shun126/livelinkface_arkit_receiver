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

    # Time-lapse recording mode
    if props.timelapse_enabled:
        props.timelapse_counter += 1

        if props.timelapse_counter >= props.timelapse_interval:
            props.timelapse_counter = 0

            # Insert key into current frame
            scene = bpy.context.scene
            current_frame = scene.frame_current

            for obj in target_objs:
                if obj and obj.data and obj.data.shape_keys:
                    for key in ARKit_BLENDSHAPES:
                        if key in obj.data.shape_keys.key_blocks:
                            kb = obj.data.shape_keys.key_blocks[key]
                            kb.keyframe_insert("value", frame=current_frame)

            # Advance the frames (to create a time-lapse video)
            scene.frame_set(current_frame + props.timelapse_interval)

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

            for i, key_name in enumerate(ARKit_BLENDSHAPES):
                if key_name in obj.data.shape_keys.key_blocks:
                    kb = obj.data.shape_keys.key_blocks[key_name]
                    kb.keyframe_insert("value", frame=scene.frame_current)
                    changed_count += 1

        self.report({'INFO'}, f"Recorded {changed_count} keys (threshold={self.threshold})")
        return {'FINISHED'}

class LFO_OT_clear_frame_keys(Operator):
    bl_idname = "livelinkface.clear_frame_keys"
    bl_label = "Clear Facial Animation Keys"
    bl_description = "Delete all shape key keyframes on the current frame for all target objects"

    def execute(self, context):
        props = context.scene.livelinkface_props
        scene = context.scene
        frame = scene.frame_current

        # 対象オブジェクト一覧
        target_objs = [item.target_object for item in props.target_objects if item.target_object]
        if not target_objs:
            target_objs = [context.object]

        deleted = 0

        for obj in target_objs:
            if not (obj and obj.data and obj.data.shape_keys):
                continue

            for key_name in ARKit_BLENDSHAPES:
                if key_name not in obj.data.shape_keys.key_blocks:
                    continue

                kb = obj.data.shape_keys.key_blocks[key_name]

                # animation_data は obj.data（=Mesh）に属する
                ad = kb.id_data.animation_data
                if not ad or not ad.action:
                    continue

                action = ad.action

                # シェイプキーに対応する FCurve を探す
                fcurve = action.fcurves.find(f'key_blocks["{key_name}"].value')
                if not fcurve:
                    continue

                # 現在フレームのキーを削除
                for kp in list(fcurve.keyframe_points):
                    if int(kp.co[0]) == frame:
                        fcurve.keyframe_points.remove(kp)
                        deleted += 1
                        break  # 同じフレームに複数キーを打つことは無いのでOK

        # UIを更新して DopeSheet / Graph Editor の表示を即時反映
        for area in bpy.context.screen.areas:
            if area.type in {'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
                area.tag_redraw()

        self.report({'INFO'}, f"Deleted {deleted} keys on frame {frame}")
        return {'FINISHED'}

class LFO_OT_clear_all_facial_keys(Operator):
    bl_idname = "livelinkface.clear_all_facial_keys"
    bl_label = "Clear ALL Facial Keys"
    bl_description = "Delete ALL keyframes for ALL ARKit shape keys on all target objects"

    def execute(self, context):
        props = context.scene.livelinkface_props

        target_objs = [item.target_object for item in props.target_objects if item.target_object]
        if not target_objs:
            target_objs = [context.object]

        deleted = 0

        for obj in target_objs:
            if not obj:
                continue

            if not obj.data.shape_keys:
                continue

            ad = obj.data.shape_keys.animation_data
            if not ad or not ad.action:
                continue

            action = ad.action

            for key_name in ARKit_BLENDSHAPES:
                path = f'key_blocks["{key_name}"].value'
                fcurve = action.fcurves.find(path)
                if fcurve:
                    deleted += len(fcurve.keyframe_points)
                    action.fcurves.remove(fcurve)

        for area in bpy.context.screen.areas:
            if area.type in {'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
                area.tag_redraw()

        self.report({'INFO'}, f"Deleted {deleted} total facial keys.")
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

                points = fcurve.keyframe_points
                last_value = None

                for kp in list(points):  # コピーで安全にループ
                    value = kp.co[1]

                    if last_value is not None:
                        if abs(value - last_value) <= self.threshold:
                            try:
                                points.remove(kp)
                                removed += 1
                            except RuntimeError:
                                for i, real_kp in enumerate(points):
                                    if real_kp.co[0] == kp.co[0] and real_kp.co[1] == kp.co[1]:
                                        points.remove(real_kp)
                                        removed += 1
                                        break
                            continue

                    last_value = value

        # UIを更新して DopeSheet / Graph Editor の表示を即時反映
        for area in bpy.context.screen.areas:
            if area.type in {'DOPESHEET_EDITOR', 'GRAPH_EDITOR'}:
                area.tag_redraw()

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
        layout.separator()
        layout.label(text="Timelapse:")
        layout.prop(props, "timelapse_enabled")
        layout.prop(props, "timelapse_interval")
        layout.separator()
        layout.operator("livelinkface.record_frame_keys", icon='KEYFRAME')
        layout.operator("livelinkface.clear_frame_keys", icon='X')
        layout.operator("livelinkface.clear_all_facial_keys", icon='TRASH')
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

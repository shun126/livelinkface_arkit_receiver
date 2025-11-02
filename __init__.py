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
from bpy.props import IntProperty, BoolProperty, StringProperty, PointerProperty, CollectionProperty
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

    target_objs = [item.target_object for item in props.target_objects if item.target_object]

    with shared_values_lock:
        global shared_values
        if shared_values:
            for obj in target_objs:
                if obj and obj.data and obj.data.shape_keys:
                    apply_blendshapes(obj, shared_values)

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
        layout.label(text="1) Set target object (name) or select object")
        layout.label(text="2) Set iPhone LiveLinkFace target to this PC:port")
        layout.label(text="3) Start and move face on iPhone")

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

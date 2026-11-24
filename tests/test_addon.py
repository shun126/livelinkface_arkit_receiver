import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import bpy
from mathutils import Euler, Quaternion


REPO_ROOT = Path(__file__).resolve().parents[1]
ADDON_PATH = REPO_ROOT / "__init__.py"
ADDON_MODULE_NAME = "livelinkface_arkit_receiver"


def load_addon():
    spec = importlib.util.spec_from_file_location(
        ADDON_MODULE_NAME,
        ADDON_PATH,
        submodule_search_locations=[str(REPO_ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load add-on from {ADDON_PATH}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[ADDON_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


def create_mesh_object(name, shape_keys):
    mesh = bpy.data.meshes.new(f"{name}Mesh")
    mesh.from_pydata([(0.0, 0.0, 0.0)], [], [])
    mesh.update()

    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    obj.shape_key_add(name="Basis")
    for key_name in shape_keys:
        obj.shape_key_add(name=key_name)

    return obj


def remove_mesh_object(obj):
    mesh = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def clear_targets(props):
    while len(props.target_objects) > 0:
        props.target_objects.remove(len(props.target_objects) - 1)


addon = load_addon()


class LiveLinkFaceAddonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        addon.register()

    @classmethod
    def tearDownClass(cls):
        props = bpy.context.scene.livelinkface_props
        clear_targets(props)
        addon.shared_values = None
        addon.unregister()

    def setUp(self):
        self.props = bpy.context.scene.livelinkface_props
        clear_targets(self.props)
        addon.shared_values = None
        if hasattr(self.props, "mirror"):
            self.props.mirror = False

    def tearDown(self):
        clear_targets(self.props)
        addon.shared_values = None
        if hasattr(self.props, "mirror"):
            self.props.mirror = False

    def test_registration_and_defaults(self):
        self.assertTrue(hasattr(bpy.context.scene, "livelinkface_props"))
        self.assertEqual(self.props.listen_ip, "0.0.0.0")
        self.assertEqual(self.props.listen_port, 11111)
        self.assertFalse(self.props.running)

    def test_apply_blendshapes_sets_matching_shape_keys(self):
        keys = ["eyeBlinkLeft", "eyeBlinkRight", "jawOpen"]
        obj = create_mesh_object("ApplyBlendshapes", keys)
        try:
            values = [0.0] * len(addon.ARKit_BLENDSHAPES)
            expected = {
                "eyeBlinkLeft": 0.25,
                "eyeBlinkRight": 0.75,
                "jawOpen": 0.5,
            }
            for key_name, value in expected.items():
                values[addon.ARKit_BLENDSHAPES.index(key_name)] = value

            addon.apply_blendshapes(obj, values)

            for key_name, value in expected.items():
                self.assertAlmostEqual(
                    obj.data.shape_keys.key_blocks[key_name].value,
                    value,
                    places=6,
                )
        finally:
            remove_mesh_object(obj)

    def test_clear_blendshapes_resets_values(self):
        keys = ["eyeBlinkLeft", "mouthSmileRight", "jawOpen"]
        obj = create_mesh_object("ClearBlendshapes", keys)
        try:
            for key_name in keys:
                obj.data.shape_keys.key_blocks[key_name].value = 0.8

            addon.clear_blendshapes(obj)

            for key_name in keys:
                self.assertAlmostEqual(
                    obj.data.shape_keys.key_blocks[key_name].value,
                    0.0,
                    places=6,
                )
        finally:
            remove_mesh_object(obj)

    def test_process_queue_applies_to_all_targets(self):
        keys = ["eyeBlinkLeft", "jawOpen"]
        objects = [
            create_mesh_object("ProcessQueueA", keys),
            create_mesh_object("ProcessQueueB", keys),
        ]
        try:
            for obj in objects:
                item = self.props.target_objects.add()
                item.target_object = obj

            values = [0.0] * len(addon.ARKit_BLENDSHAPES)
            values[addon.ARKit_BLENDSHAPES.index("eyeBlinkLeft")] = 0.3
            values[addon.ARKit_BLENDSHAPES.index("jawOpen")] = 0.6
            addon.shared_values = tuple(values)

            next_interval = addon.process_queue()

            self.assertIsNone(next_interval)
            for obj in objects:
                self.assertAlmostEqual(
                    obj.data.shape_keys.key_blocks["eyeBlinkLeft"].value,
                    0.3,
                    places=6,
                )
                self.assertAlmostEqual(
                    obj.data.shape_keys.key_blocks["jawOpen"].value,
                    0.6,
                    places=6,
                )
        finally:
            clear_targets(self.props)
            for obj in objects:
                remove_mesh_object(obj)

    def test_process_queue_applies_to_non_mesh_shape_keys(self):
        lattice = bpy.data.lattices.new("ShapeKeyLattice")
        obj = bpy.data.objects.new("ShapeKeyLattice", lattice)
        bpy.context.scene.collection.objects.link(obj)
        try:
            obj.shape_key_add(name="Basis")
            obj.shape_key_add(name="jawOpen")
            item = self.props.target_objects.add()
            item.target_object = obj

            values = [0.0] * len(addon.ARKit_BLENDSHAPES)
            values[addon.ARKit_BLENDSHAPES.index("jawOpen")] = 0.6
            addon.shared_values = tuple(values)

            addon.process_queue()

            self.assertAlmostEqual(lattice.shape_keys.key_blocks["jawOpen"].value, 0.6, places=6)
        finally:
            clear_targets(self.props)
            bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.lattices.remove(lattice)

    def test_mirror_feature_contract_when_present(self):
        if not hasattr(self.props, "mirror"):
            self.skipTest("Mirror feature is not present in this revision")

        pair_type = getattr(addon, "LeftRightBlendshapeIdxs", None)
        self.assertIsNotNone(pair_type, "Mirror feature must define LeftRightBlendshapeIdxs")
        self.assertEqual(
            pair_type.__annotations__,
            {"Left": int, "Right": int},
            "Blendshape indexes must be typed as integers",
        )

        mirror_property = self.props.bl_rna.properties.get("mirror")
        self.assertIsNotNone(mirror_property)
        self.assertEqual(mirror_property.name, "Mirror Left/Right")
        self.assertEqual(
            mirror_property.description,
            "Swap left and right ARKit blendshape values",
        )

    def test_mirror_swaps_left_and_right_when_present(self):
        if not hasattr(self.props, "mirror"):
            self.skipTest("Mirror feature is not present in this revision")

        obj = create_mesh_object(
            "MirrorBlendshapes",
            ["eyeBlinkLeft", "eyeBlinkRight"],
        )
        try:
            item = self.props.target_objects.add()
            item.target_object = obj

            values = [0.0] * len(addon.ARKit_BLENDSHAPES)
            values[addon.ARKit_BLENDSHAPES.index("eyeBlinkLeft")] = 0.2
            values[addon.ARKit_BLENDSHAPES.index("eyeBlinkRight")] = 0.8
            addon.shared_values = tuple(values)
            self.props.mirror = True

            addon.process_queue()

            self.assertAlmostEqual(
                obj.data.shape_keys.key_blocks["eyeBlinkLeft"].value,
                0.8,
                places=6,
            )
            self.assertAlmostEqual(
                obj.data.shape_keys.key_blocks["eyeBlinkRight"].value,
                0.2,
                places=6,
            )
        finally:
            clear_targets(self.props)
            remove_mesh_object(obj)


class RecordingLayout:
    """UILayout の代わりに draw() の呼び出しを記録する"""

    def __init__(self, log):
        self.log = log
        self.active = True

    def _child(self, *args, **kwargs):
        return RecordingLayout(self.log)

    row = column = box = _child

    def label(self, text="", **kwargs):
        self.log.append(("label", None, text, None))

    def separator(self, **kwargs):
        pass

    def template_list(self, *args, **kwargs):
        pass

    def operator(self, name, **kwargs):
        self.log.append(("operator", None, name, kwargs.get("icon")))

    def panel(self, idname, default_closed=False):
        self.log.append(("panel", None, idname, default_closed))
        return RecordingLayout(self.log), RecordingLayout(self.log)

    def prop(self, data, name, **kwargs):
        self.log.append(("prop", data, name, kwargs.get("icon")))

    def prop_search(self, data, name, search_data, search_name, **kwargs):
        self.log.append(("prop_search", data, name, search_name))


def create_armature(name, bones):
    """bones: {ボーン名: tail}。head は原点"""
    armature = bpy.data.armatures.new(f"{name}Data")
    obj = bpy.data.objects.new(name, armature)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    for bone_name, tail in bones.items():
        bone = armature.edit_bones.new(bone_name)
        bone.head = (0.0, 0.0, 0.0)
        bone.tail = tail
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj


def remove_armature(obj):
    armature = obj.data
    action = obj.animation_data.action if obj.animation_data else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if armature.users == 0:
        bpy.data.armatures.remove(armature)
    if action and action.users == 0:
        bpy.data.actions.remove(action)


FACE_BONES = {
    "eye.L": (0.0, -1.0, 0.0),
    "eye.R": (0.0, -1.0, 0.0),
    "neck": (0.0, 0.0, 1.0),
    "head": (0.0, 0.0, 1.0),
}
RESET_PROPS = (
    "armature_object", "eye_bone_left", "eye_bone_right", "neck_bone", "head_bone",
    "apply_eye_bones", "apply_head_bones", "neck_weight", "eye_scale", "head_scale",
    "write_custom_props", "mirror", "timelapse_enabled", "timelapse_interval", "timelapse_counter",
    "eye_pitch_axis", "eye_yaw_axis", "eye_roll_axis",
    "eye_pitch_invert", "eye_yaw_invert", "eye_roll_invert",
    "head_pitch_axis", "head_yaw_axis", "head_roll_axis",
    "head_pitch_invert", "head_yaw_invert", "head_roll_invert",
)


def rotation_values():
    values = [0.0] * addon.LIVELINK_VALUE_COUNT
    values[addon.HEAD_YAW] = 0.10
    values[addon.HEAD_PITCH] = 0.20
    values[addon.HEAD_ROLL] = -0.30
    values[addon.L_EYE_YAW] = 0.11
    values[addon.L_EYE_PITCH] = 0.12
    values[addon.L_EYE_ROLL] = 0.13
    values[addon.R_EYE_YAW] = -0.21
    values[addon.R_EYE_PITCH] = 0.22
    values[addon.R_EYE_ROLL] = -0.23
    return values


class LiveLinkFaceBoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        addon.register()

    @classmethod
    def tearDownClass(cls):
        clear_targets(bpy.context.scene.livelinkface_props)
        addon.shared_values = None
        addon.unregister()

    def setUp(self):
        self.props = bpy.context.scene.livelinkface_props
        self.reset_props()
        bpy.context.scene.frame_set(1)
        self.arm = create_armature("FaceRig", FACE_BONES)
        for bone in self.arm.pose.bones:
            bone.rotation_mode = 'XYZ'
        self.props.armature_object = self.arm
        self.props.apply_eye_bones = True
        self.props.apply_head_bones = True
        self.props.neck_bone = "neck"
        self.props.head_bone = "head"

    def tearDown(self):
        self.reset_props()
        remove_armature(self.arm)

    def reset_props(self):
        clear_targets(self.props)
        addon.shared_values = None
        for name in RESET_PROPS:
            self.props.property_unset(name)

    def assertEuler(self, bone, expected):
        for actual, value in zip(bone.rotation_euler, expected):
            self.assertAlmostEqual(actual, value, places=5)

    def fcurve(self, bone_name, prop="rotation_euler", index=0):
        fcurves = addon.get_fcurves(self.arm)
        if fcurves is None:
            return None
        return fcurves.find(f'pose.bones["{bone_name}"].{prop}', index=index)

    def test_axis_mapping_and_sign(self):
        self.props.neck_bone = ""
        self.props.eye_yaw_invert = True
        addon.apply_bones(self.arm, rotation_values(), self.props)

        bones = self.arm.pose.bones
        # 目: Pitch→X, Roll→Y, Yaw→Z（Yaw は符号反転）
        self.assertEuler(bones["eye.L"], (0.12, 0.13, -0.11))
        self.assertEuler(bones["eye.R"], (0.22, -0.23, 0.21))
        # 頭: Pitch→X, Yaw→Y, Roll→Z
        self.assertEuler(bones["head"], (0.20, 0.10, -0.30))

    def test_scale_is_applied(self):
        self.props.neck_bone = ""
        self.props.eye_scale = 2.0
        self.props.head_scale = 0.5
        addon.apply_bones(self.arm, rotation_values(), self.props)

        self.assertEuler(self.arm.pose.bones["eye.L"], (0.24, 0.26, 0.22))
        self.assertEuler(self.arm.pose.bones["head"], (0.10, 0.05, -0.15))

    def test_rotation_mode_is_preserved(self):
        expected = Euler((0.12, 0.13, 0.11), 'XYZ').to_quaternion()
        for mode in ('QUATERNION', 'AXIS_ANGLE', 'ZXY'):
            bone = self.arm.pose.bones["eye.L"]
            bone.rotation_mode = mode
            addon.apply_bones(self.arm, rotation_values(), self.props)

            self.assertEqual(bone.rotation_mode, mode)
            if mode == 'QUATERNION':
                actual = bone.rotation_quaternion
            elif mode == 'AXIS_ANGLE':
                angle, x, y, z = bone.rotation_axis_angle
                actual = Quaternion((x, y, z), angle)
            else:
                actual = bone.rotation_euler.to_quaternion()
            self.assertAlmostEqual(abs(actual.dot(expected)), 1.0, places=5)

    def test_mirror_swaps_eyes_and_negates_yaw_roll(self):
        self.props.neck_bone = ""
        self.props.mirror = True
        addon.shared_values = tuple(rotation_values())

        addon.process_queue()

        bones = self.arm.pose.bones
        self.assertEuler(bones["eye.L"], (0.22, 0.23, 0.21))
        self.assertEuler(bones["eye.R"], (0.12, -0.13, -0.11))
        self.assertEuler(bones["head"], (0.20, -0.10, 0.30))

    def test_neck_weight_distribution(self):
        values = rotation_values()
        addon.apply_bones(self.arm, values, self.props)
        self.assertEuler(self.arm.pose.bones["neck"], (0.08, 0.04, -0.12))
        self.assertEuler(self.arm.pose.bones["head"], (0.12, 0.06, -0.18))

        self.props.neck_bone = ""
        addon.apply_bones(self.arm, values, self.props)
        self.assertEuler(self.arm.pose.bones["head"], (0.20, 0.10, -0.30))

    def test_missing_neck_bone_gives_head_full_rotation(self):
        self.props.neck_bone = "does_not_exist"
        addon.apply_bones(self.arm, rotation_values(), self.props)
        self.assertEuler(self.arm.pose.bones["head"], (0.20, 0.10, -0.30))

    def test_short_packet_does_not_raise(self):
        self.props.write_custom_props = True
        self.props.mirror = True
        addon.shared_values = tuple([0.5] * len(addon.ARKit_BLENDSHAPES))

        addon.process_queue()

        self.assertEuler(self.arm.pose.bones["eye.L"], (0.0, 0.0, 0.0))
        self.assertNotIn("headYaw", self.arm)

    def test_armature_in_both_slots_is_applied_once(self):
        item = self.props.target_objects.add()
        item.target_object = self.arm
        self.assertEqual(addon.get_target_armatures(self.props), [self.arm])

    def test_custom_properties_keep_negative_values(self):
        self.props.write_custom_props = True
        values = rotation_values()
        addon.shared_values = tuple(values)

        addon.process_queue()

        self.assertEqual(len(addon.CUSTOM_PROPERTY_INDICES), 9)
        for name, index in addon.CUSTOM_PROPERTY_INDICES:
            self.assertAlmostEqual(self.arm[name], values[index], places=6)
        self.assertLess(self.arm["headRoll"], 0.0)

    def test_record_clear_frame_and_clear_all_keys(self):
        bone = self.arm.pose.bones["eye.L"]
        scene = bpy.context.scene

        # フレーム変更時にアニメーションが再評価されるので、ポーズは移動後に設定する
        scene.frame_set(1)
        bone.rotation_euler = (0.1, 0.0, 0.0)
        bpy.ops.livelinkface.record_frame_keys(threshold=0.001)
        scene.frame_set(10)
        bone.rotation_euler = (0.5, 0.0, 0.0)
        bpy.ops.livelinkface.record_frame_keys(threshold=0.001)
        self.assertEqual(len(self.fcurve("eye.L").keyframe_points), 2)

        bpy.ops.livelinkface.clear_frame_keys()
        self.assertEqual([p.co[0] for p in self.fcurve("eye.L").keyframe_points], [1.0])

        bpy.ops.livelinkface.clear_all_facial_keys()
        self.assertIsNone(self.fcurve("eye.L"))

    def test_clear_frame_keeps_subframe_keys(self):
        bone = self.arm.pose.bones["eye.L"]
        for frame, value in ((10.0, 0.1), (10.5, 0.5)):
            bone.rotation_euler = (value, 0.0, 0.0)
            bone.keyframe_insert("rotation_euler", index=0, frame=frame)
        bpy.context.scene.frame_set(10)

        bpy.ops.livelinkface.clear_frame_keys()
        bpy.ops.livelinkface.clear_frame_keys()

        self.assertEqual([p.co[0] for p in self.fcurve("eye.L").keyframe_points], [10.5])

    def test_key_editing_operators_support_undo(self):
        for op_class in (
            addon.LFO_OT_clear_shape_keys,
            addon.LFO_OT_record_frame_keys,
            addon.LFO_OT_clear_frame_keys,
            addon.LFO_OT_clear_all_facial_keys,
            addon.LFO_OT_cleanup_keys,
        ):
            with self.subTest(operator=op_class.bl_idname):
                self.assertIn('UNDO', op_class.bl_options)

    def test_record_threshold_skips_unchanged_values(self):
        bone = self.arm.pose.bones["eye.L"]
        scene = bpy.context.scene

        scene.frame_set(1)
        bone.rotation_euler = (0.1, 0.2, 0.3)
        bpy.ops.livelinkface.record_frame_keys(threshold=0.01)
        scene.frame_set(5)
        bone.rotation_euler = (0.105, 0.2, 0.9)
        bpy.ops.livelinkface.record_frame_keys(threshold=0.01)

        self.assertEqual(len(self.fcurve("eye.L", index=0).keyframe_points), 1)
        self.assertEqual(len(self.fcurve("eye.L", index=2).keyframe_points), 2)

    def test_record_updates_existing_key_on_same_frame(self):
        bone = self.arm.pose.bones["eye.L"]
        bone.rotation_euler = (0.1, 0.0, 0.0)
        bpy.context.scene.frame_current = 1
        bpy.ops.livelinkface.record_frame_keys(threshold=0.01)
        bone.rotation_euler = (0.105, 0.0, 0.0)
        bpy.ops.livelinkface.record_frame_keys(threshold=0.01)

        points = self.fcurve("eye.L").keyframe_points
        self.assertEqual(len(points), 1)
        self.assertAlmostEqual(points[0].co[1], 0.105, places=5)

    def test_quaternion_bone_keys_use_all_components(self):
        bone = self.arm.pose.bones["head"]
        bone.rotation_mode = 'QUATERNION'
        bpy.ops.livelinkface.record_frame_keys(threshold=0.0)
        for index in range(4):
            self.assertIsNotNone(self.fcurve("head", "rotation_quaternion", index))

    def test_cleanup_removes_redundant_bone_keys(self):
        bone = self.arm.pose.bones["eye.L"]
        for frame, value in ((1, 0.1), (2, 0.1), (3, 0.1), (4, 0.9), (5, 0.9)):
            bone.rotation_euler = (value, 0.0, 0.0)
            bone.keyframe_insert("rotation_euler", index=0, frame=frame)

        bpy.ops.livelinkface.cleanup_keys(threshold=0.001)

        # 2 だけが不要。3 はホールドの終わり、5 は最後のキーなので残す
        self.assertEqual([p.co[0] for p in self.fcurve("eye.L").keyframe_points], [1.0, 3.0, 4.0, 5.0])

    def test_cleanup_preserves_hold_boundaries(self):
        bone = self.arm.pose.bones["eye.L"]
        for frame, value in ((1, 0.0), (25, 0.0), (50, 0.0), (51, 1.0), (100, 1.0)):
            bone.rotation_euler = (value, 0.0, 0.0)
            bone.keyframe_insert("rotation_euler", index=0, frame=frame)

        bpy.ops.livelinkface.cleanup_keys(threshold=0.0)

        fcurve = self.fcurve("eye.L")
        self.assertEqual([p.co[0] for p in fcurve.keyframe_points], [1.0, 50.0, 51.0, 100.0])
        self.assertAlmostEqual(fcurve.evaluate(40), 0.0, places=5)

    def test_cleanup_does_not_drift_on_slow_changes(self):
        bone = self.arm.pose.bones["eye.L"]
        for frame in range(1, 11):
            bone.rotation_euler = (frame * 0.0003, 0.0, 0.0)
            bone.keyframe_insert("rotation_euler", index=0, frame=frame)

        bpy.ops.livelinkface.cleanup_keys(threshold=0.001)

        values = [p.co[1] for p in self.fcurve("eye.L").keyframe_points]
        self.assertLess(len(values), 10)
        for previous, current in zip(values, values[1:]):
            self.assertLessEqual(current - previous, 0.001 + 1e-6)

    def receive(self, values):
        """受信スレッドがパケットを受け取ったときと同じように shared_values を更新する"""
        addon.shared_values = tuple(values)
        addon.shared_values_serial += 1

    def test_timelapse_keys_bones(self):
        self.props.timelapse_enabled = True
        self.props.timelapse_interval = 1
        self.receive(rotation_values())

        addon.process_queue()

        self.assertIsNotNone(self.fcurve("eye.L"))
        self.assertEqual(bpy.context.scene.frame_current, 2)

    def test_timelapse_waits_for_first_packet(self):
        self.props.timelapse_enabled = True
        self.props.timelapse_interval = 1

        addon.process_queue()

        self.assertIsNone(self.fcurve("eye.L"))
        self.assertEqual(bpy.context.scene.frame_current, 1)

    def test_timelapse_does_not_record_stale_values(self):
        self.props.timelapse_enabled = True
        self.props.timelapse_interval = 1
        self.receive(rotation_values())
        addon.process_queue()

        # 新しいパケットが届かない間は記録もフレームの前進もしない
        addon.process_queue()
        addon.process_queue()
        self.assertEqual(bpy.context.scene.frame_current, 2)
        self.assertEqual(len(self.fcurve("eye.L").keyframe_points), 1)

        self.receive(rotation_values())
        addon.process_queue()
        self.assertEqual(bpy.context.scene.frame_current, 3)
        self.assertEqual(len(self.fcurve("eye.L").keyframe_points), 2)

    def test_shape_key_operators_work_with_layered_actions(self):
        obj = create_mesh_object("LayeredKeys", ["jawOpen"])
        try:
            item = self.props.target_objects.add()
            item.target_object = obj
            key = obj.data.shape_keys.key_blocks["jawOpen"]
            key.value = 0.5
            bpy.context.scene.frame_current = 3
            bpy.ops.livelinkface.record_frame_keys(threshold=0.001)

            fcurves = addon.get_fcurves(obj.data.shape_keys)
            self.assertIsNotNone(fcurves.find('key_blocks["jawOpen"].value'))

            bpy.ops.livelinkface.clear_frame_keys()
            self.assertIsNone(fcurves.find('key_blocks["jawOpen"].value'))
        finally:
            clear_targets(self.props)
            remove_mesh_object(obj)

    def test_armature_target_does_not_break_shape_key_clear(self):
        item = self.props.target_objects.add()
        item.target_object = self.arm
        self.assertEqual(bpy.ops.livelinkface.clear_shape_keys(), {'FINISHED'})

    def test_bones_panel_draw_uses_valid_properties(self):
        log = []
        addon.LFO_PT_panel.draw(SimpleNamespace(layout=RecordingLayout(log)), bpy.context)

        icons = bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
        for kind, data, name, extra in log:
            if kind in ("prop", "prop_search"):
                self.assertIn(name, data.bl_rna.properties, name)
            if kind == "prop" and extra:
                self.assertIn(extra, icons)
        searched = {name for kind, _, name, _ in log if kind == "prop_search"}
        self.assertEqual(searched, {"eye_bone_left", "eye_bone_right", "neck_bone", "head_bone"})

    def test_panel_order_puts_start_after_settings(self):
        self.assertIn("panel", bpy.types.UILayout.bl_rna.functions)
        log = []
        addon.LFO_PT_panel.draw(SimpleNamespace(layout=RecordingLayout(log)), bpy.context)

        names = [name for _, _, name, _ in log]
        order = [
            names.index(name)
            for name in (
                "livelinkface.clear_shape_keys",
                "mirror",
                "LFO_bones",
                "LFO_timelapse",
                "timelapse_enabled",
                "livelinkface.record_frame_keys",
                "livelinkface.clear_frame_keys",
                "livelinkface.clear_all_facial_keys",
                "livelinkface.cleanup_keys",
                "livelinkface.start",
            )
        ]
        self.assertEqual(order, sorted(order))
        collapsible = {name: closed for kind, _, name, closed in log if kind == "panel"}
        self.assertEqual(collapsible, {"LFO_bones": True, "LFO_timelapse": True})


if __name__ == "__main__":
    suite = unittest.TestSuite()
    for case in (LiveLinkFaceAddonTests, LiveLinkFaceBoneTests):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)

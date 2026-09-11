import importlib.util
import sys
import unittest
from pathlib import Path

import bpy


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


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(LiveLinkFaceAddonTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)

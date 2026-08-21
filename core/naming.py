from __future__ import annotations

import string


def _get_addon_module_name():
    package = __package__ if __package__ else __name__
    parts = package.split(".")
    if len(parts) >= 3 and parts[0] == "bl_ext":
        return ".".join(parts[:3])
    return parts[0]


def _get_prefs(context):
    addon_name = _get_addon_module_name()
    addon = context.preferences.addons.get(addon_name) if context and context.preferences else None
    return addon.preferences if addon else None


def get_unique_collection_name(base_name: str) -> str:
    import bpy

    if base_name not in bpy.data.collections:
        return base_name

    counter = 1
    while True:
        new_name = f"{base_name}_{counter:02d}"
        if new_name not in bpy.data.collections:
            return new_name
        counter += 1


def ensure_collection(context, name: str):
    import bpy

    if name in bpy.data.collections:
        return bpy.data.collections[name]

    new_coll = bpy.data.collections.new(name)
    context.scene.collection.children.link(new_coll)
    return new_coll


class NamingManager:
    @staticmethod
    def _batch_prefix(context) -> str:
        prefs = _get_prefs(context)
        return getattr(prefs, "batch_prefix", "立牌批次") if prefs else "立牌批次"

    @staticmethod
    def _model_prefix(context) -> str:
        prefs = _get_prefs(context)
        return getattr(prefs, "model_prefix", "亚克力") if prefs else "亚克力"

    @staticmethod
    def get_batch_collection_name(timestamp: str, context=None) -> str:
        return f"{NamingManager._batch_prefix(context)}_{timestamp}"

    @staticmethod
    def _plane_prefix(context) -> str:
        prefs = _get_prefs(context)
        return getattr(prefs, "plane_prefix", "图案") if prefs else "图案"

    @staticmethod
    def get_model_collection_name(index: int, name_pure: str, context=None) -> str:
        return f"{NamingManager._model_prefix(context)}_{index:02d}_{name_pure}"

    @staticmethod
    def get_plane_obj_name(index: int, name_pure: str, context=None) -> str:
        return f"{NamingManager._plane_prefix(context)}_{index:02d}_{name_pure}"

    @staticmethod
    def get_rainbow_obj_name(source_obj_name: str) -> str:
        return f"彩窗_{source_obj_name}"

    @staticmethod
    def is_script_generated_collection(collection_name: str, context=None) -> bool:
        if not collection_name:
            return False

        batch_prefix = NamingManager._batch_prefix(context)
        model_prefix = NamingManager._model_prefix(context)
        return collection_name.startswith(f"{batch_prefix}_") or collection_name.startswith(f"{model_prefix}_")

    @staticmethod
    def increment_batch_sequence():
        import bpy

        scene = getattr(bpy.context, "scene", None)
        props = getattr(scene, "acrylic_props", None) if scene else None
        if not props:
            return

        try:
            props.batch_sequence_number += 1
        except Exception:
            return

    @staticmethod
    def get_batch_sequence_token() -> str:
        import bpy

        scene = getattr(bpy.context, "scene", None)
        props = getattr(scene, "acrylic_props", None) if scene else None
        n = getattr(props, "batch_sequence_number", 0) if props else 0
        return f"{n:02d}"

    @staticmethod
    def get_alpha_token() -> str:
        token = NamingManager.get_batch_sequence_token()
        try:
            idx = int(token) - 1
        except Exception:
            idx = 0
        idx = max(0, idx)
        letters = string.ascii_uppercase
        return letters[idx % len(letters)]


from __future__ import annotations

import os
import shutil
from pathlib import Path

import bpy


def get_temp_dir() -> str:
    base = Path(bpy.app.tempdir) if bpy.app.tempdir else Path(os.path.expanduser("~"))
    return str(base / "digital_merch_factory_temp")


def get_assets_dir() -> str:
    if bpy.data.filepath:
        base_dir = Path(bpy.data.filepath).resolve().parent
    else:
        base_dir = Path(bpy.path.abspath("//") or os.path.expanduser("~")).resolve()

    return str(base_dir / "(勿删)赛博谷子工厂压缩素材")


def ensure_dir(path: str) -> str:
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def clean_temp_folder(temp_dir: str):
    if not temp_dir:
        return

    if not os.path.exists(temp_dir):
        return

    for filename in os.listdir(temp_dir):
        file_path = os.path.join(temp_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception:
            continue


def update_ui(context, message: str):
    try:
        props = context.scene.acrylic_props
        props.status_text = message
    except Exception:
        pass

    try:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                area.tag_redraw()
    except Exception:
        pass

    try:
        bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
    except Exception:
        pass


def show_error_popup(context, message: str):
    def draw(self, _context):
        self.layout.label(text=message)

    try:
        context.window_manager.popup_menu(draw, title="脚本运行错误", icon="ERROR")
    except Exception:
        pass


from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ..utils import blender_utils
from ..utils import system


def _startupinfo():
    if os.name != "nt":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    return info


def process_image(context, image_path: str):
    props = context.scene.acrylic_props

    if not image_path:
        return None

    image_path = os.path.abspath(image_path)
    if not os.path.exists(image_path):
        return None

    name_pure = os.path.splitext(os.path.basename(image_path))[0]

    assets_dir = blender_utils.ensure_dir(blender_utils.get_assets_dir())
    temp_dir = blender_utils.ensure_dir(blender_utils.get_temp_dir())

    svg_path = os.path.join(assets_dir, f"{name_pure}.svg")
    tex_path = os.path.join(assets_dir, f"{name_pure}_tex_72dpi.png")
    mask_path = os.path.join(temp_dir, f"{name_pure}_mask.bmp")

    magick_exe = system.get_magick_exe_path()
    potrace_exe = system.get_potrace_exe_path()

    blender_utils.update_ui(context, f"正在处理图片: {os.path.basename(image_path)}")

    magick_cmd = [
        magick_exe,
        image_path,
        "-resize",
        "x1000",
        "-density",
        "72",
        "-units",
        "PixelsPerInch",
        "+write",
        tex_path,
        "-alpha",
        "extract",
    ]

    if getattr(props, "offset_px", 0) > 0:
        magick_cmd.extend(["-morphology", "Dilate", f"Disk:{int(props.offset_px)}"])

    if getattr(props, "smoothing_px", 0) > 0:
        magick_cmd.extend(["-blur", f"0x{int(props.smoothing_px)}"])

    threshold = int(getattr(props, "threshold", 60))
    magick_cmd.extend(
        [
            "-threshold",
            f"{threshold}%",
            "-negate",
            "-depth",
            "8",
            mask_path,
        ]
    )

    magick_result = subprocess.run(
        magick_cmd,
        capture_output=True,
        text=True,
        shell=False,
        startupinfo=_startupinfo(),
    )
    if magick_result.returncode != 0 or (not os.path.exists(mask_path)):
        raise RuntimeError(magick_result.stderr.strip() if magick_result.stderr else "图片处理失败")

    blender_utils.update_ui(context, "正在生成矢量路径...")

    potrace_cmd = [potrace_exe, mask_path, "-s", "--flat", "-o", svg_path]
    potrace_result = subprocess.run(
        potrace_cmd,
        capture_output=True,
        text=True,
        shell=False,
        startupinfo=_startupinfo(),
    )
    if potrace_result.returncode != 0 or (not os.path.exists(svg_path)):
        raise RuntimeError(potrace_result.stderr.strip() if potrace_result.stderr else "转矢量失败")

    if not os.path.exists(tex_path):
        raise RuntimeError("贴图生成失败")

    return name_pure, svg_path, tex_path


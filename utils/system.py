from __future__ import annotations

import os
from pathlib import Path


def _addon_root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def get_tools_dir() -> str:
    return str(_addon_root_dir() / "tools")


def get_magick_exe_path() -> str:
    return str(Path(get_tools_dir()) / "magick.exe")


def get_potrace_exe_path() -> str:
    return str(Path(get_tools_dir()) / "potrace.exe")


def check_tools_exist():
    missing = []

    if not os.path.exists(get_magick_exe_path()):
        missing.append("magick.exe")

    if not os.path.exists(get_potrace_exe_path()):
        missing.append("potrace.exe")

    return missing


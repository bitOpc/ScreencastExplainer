"""读写 presenter.json、半身照落盘与耗时估算。"""

import json
import shutil
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".screencast-explainer"

_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}


def presenter_config_path() -> Path:
    return CONFIG_DIR / "presenter.json"


def default_presenter_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "installed": False,
        "sadtalker_root": "~/.sadtalker",
        "has_cuda": False,
        "avatar_image": None,
        "layout": {
            "position": "bottom-right",
            "width_ratio": 0.18,
            "margin_px": 24,
            "shape": "circle",
        },
        "sadtalker": {
            "still": True,
            "preprocess": "full",
            "face_model_resolution": 512,
        },
    }


def load_presenter_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or presenter_config_path()
    if not config_path.is_file():
        return default_presenter_config()
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_presenter_config(data: dict[str, Any], path: Path | None = None) -> None:
    config_path = path or presenter_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def estimate_avatar_minutes(
    audio_seconds: float, *, has_cuda: bool
) -> dict[str, Any]:
    if has_cuda:
        min_minutes = audio_seconds * 2 / 60
        max_minutes = audio_seconds * 4 / 60
        label = f"预估约 {min_minutes:.0f}–{max_minutes:.0f} 分钟"
        return {
            "label": label,
            "min_minutes": min_minutes,
            "max_minutes": max_minutes,
            "needs_slow_confirm": False,
        }

    return {
        "label": "可能数小时",
        "min_minutes": None,
        "max_minutes": None,
        "needs_slow_confirm": True,
    }


def install_avatar_image(src: Path, dest: Path | None = None) -> Path:
    if src.suffix not in _ALLOWED_IMAGE_SUFFIXES:
        raise ValueError(f"不支持的图片格式: {src.suffix}")

    target = dest or (CONFIG_DIR / "avatars" / "default.png")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, target)
    return target

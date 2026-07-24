"""读写 presenter.json、半身照落盘与耗时估算。"""

import json
import shutil
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".screencast-explainer"

_ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".JPG", ".JPEG", ".PNG"}

# PiP 小窗默认走 fast：256 + crop + batch_size=4（相对主画面约 18% 足够清晰）
SADTALKER_PROFILES: dict[str, dict[str, Any]] = {
    "fast": {
        "still": True,
        "preprocess": "crop",
        "face_model_resolution": 256,
        "batch_size": 4,
    },
    "balanced": {
        "still": True,
        "preprocess": "full",
        "face_model_resolution": 256,
        "batch_size": 4,
    },
    "quality": {
        "still": True,
        "preprocess": "full",
        "face_model_resolution": 512,
        "batch_size": 2,
    },
}

# 构图模式 → SadTalker still/preprocess（由 Agent 裁切预览后用户选择）
FRAMING_MODES: dict[str, dict[str, Any]] = {
    "head": {
        "label": "头部特写",
        "still": False,
        "preprocess": "crop",
        "description": "脸部特写；头姿可动，口型最自然",
    },
    "medium": {
        "label": "中景",
        "still": True,
        "preprocess": "full",
        "description": "肩以上 + 背景；锁姿态，避免头身脱节",
    },
    "full": {
        "label": "全景",
        "still": True,
        "preprocess": "full",
        "description": "尽量全身/最大画幅；锁姿态，只动嘴",
    },
}


def presenter_config_path() -> Path:
    return CONFIG_DIR / "presenter.json"


def default_presenter_config() -> dict[str, Any]:
    return {
        "enabled": False,
        "installed": False,
        "sadtalker_root": "~/.sadtalker",
        "has_cuda": False,
        "avatar_image": None,
        "profile": "fast",
        "layout": {
            "position": "bottom-right",
            "width_ratio": 0.18,
            "margin_px": 24,
            "shape": "circle",
        },
        "sadtalker": dict(SADTALKER_PROFILES["fast"]),
    }


def resolve_sadtalker_settings(config: dict[str, Any]) -> dict[str, Any]:
    """按 profile / framing_mode 合并 sadtalker；无 CUDA 时限制 batch_size≤2。"""
    profile_name = str(config.get("profile") or "fast")
    base = dict(SADTALKER_PROFILES.get(profile_name, SADTALKER_PROFILES["fast"]))
    framing_mode = config.get("framing_mode")
    if framing_mode:
        framing = FRAMING_MODES.get(str(framing_mode))
        if framing is None:
            raise ValueError(
                f"未知 framing_mode: {framing_mode}；可选: {', '.join(FRAMING_MODES)}"
            )
        base["still"] = bool(framing["still"])
        base["preprocess"] = str(framing["preprocess"])
    overrides = config.get("sadtalker") or {}
    if isinstance(overrides, dict):
        base.update(overrides)
    batch_size = int(base.get("batch_size", 4))
    if not config.get("has_cuda"):
        batch_size = min(batch_size, 2)
    base["batch_size"] = max(1, batch_size)
    base["still"] = bool(base.get("still", True))
    base["preprocess"] = str(base.get("preprocess", "crop"))
    base["face_model_resolution"] = int(base.get("face_model_resolution", 256))
    return base


def framing_sadtalker_params(framing_mode: str) -> dict[str, Any]:
    """返回某构图模式对应的 still/preprocess（不含分辨率档位）。"""
    framing = FRAMING_MODES.get(framing_mode)
    if framing is None:
        raise ValueError(
            f"未知 framing_mode: {framing_mode}；可选: {', '.join(FRAMING_MODES)}"
        )
    return {
        "still": bool(framing["still"]),
        "preprocess": str(framing["preprocess"]),
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
        # 默认 fast 档（256/crop/batch=4）相对旧 512/full 更快；仍按保守区间告知用户
        min_minutes = audio_seconds * 1.5 / 60
        max_minutes = audio_seconds * 3 / 60
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

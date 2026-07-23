#!/usr/bin/env python3
"""依赖检查：ffmpeg、ffprobe、screencapture、edge-tts、中文字体。"""

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import ImageFont

from lib.presenter_config import load_presenter_config, presenter_config_path

DEFAULT_VOICE_ID = "zh-CN-YunxiNeural"
DEFAULT_VOICE_RATE = "-3%"


def _available(binary: str) -> bool:
    return shutil.which(binary) is not None


def _edge_tts_available() -> bool:
    return importlib.util.find_spec("edge_tts") is not None


def _cjk_font_available() -> bool:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                ImageFont.truetype(path, 24)
                return True
            except OSError:
                continue
    return False


def _presenter_status() -> dict[str, str]:
    """返回可选 Presenter 能力状态，不将其作为主流程依赖。"""
    config_path = presenter_config_path()
    if not config_path.is_file():
        return {
            "presenter_enabled": "not_configured",
            "presenter_installed": "not_configured",
            "presenter_has_cuda": "not_configured",
            "presenter_avatar": "not_configured",
        }

    try:
        config = load_presenter_config(config_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "presenter_enabled": "unavailable",
            "presenter_installed": "unavailable",
            "presenter_has_cuda": "unavailable",
            "presenter_avatar": "unavailable",
        }

    installed = bool(config.get("installed"))
    avatar_image = config.get("avatar_image")
    avatar_status = "not_configured"
    if avatar_image:
        avatar_status = (
            "available" if Path(str(avatar_image)).expanduser().is_file() else "unavailable"
        )

    return {
        "presenter_enabled": "available"
        if config.get("enabled")
        else "unavailable",
        "presenter_installed": "available" if installed else "not_configured",
        "presenter_has_cuda": (
            "available"
            if config.get("has_cuda")
            else "unavailable"
            if installed
            else "not_configured"
        ),
        "presenter_avatar": avatar_status,
    }


def check_dependencies() -> dict[str, str]:
    edge = _edge_tts_available()
    result = {
        "python3": "available",
        "ffmpeg": "available" if _available("ffmpeg") else "unavailable",
        "ffprobe": "available" if _available("ffprobe") else "unavailable",
        "screencapture": "available" if _available("screencapture") else "unavailable",
        "edge_tts": "available" if edge else "unavailable",
        "cjk_font": "available" if _cjk_font_available() else "unavailable",
        "selected_voice": DEFAULT_VOICE_ID if edge else "unavailable",
        "selected_voice_rate": DEFAULT_VOICE_RATE if edge else "unavailable",
    }
    result.update(_presenter_status())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Screencast Explainer 依赖")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()
    result = check_dependencies()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    required = ["ffmpeg", "ffprobe", "edge_tts", "screencapture"]
    if any(result[k] == "unavailable" for k in required):
        sys.exit(1)


if __name__ == "__main__":
    main()

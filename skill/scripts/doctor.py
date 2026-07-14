#!/usr/bin/env python3
"""依赖检查：ffmpeg、ffprobe、screencapture、edge-tts、中文字体。"""

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import ImageFont

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


def check_dependencies() -> dict[str, str]:
    edge = _edge_tts_available()
    return {
        "python3": "available",
        "ffmpeg": "available" if _available("ffmpeg") else "unavailable",
        "ffprobe": "available" if _available("ffprobe") else "unavailable",
        "screencapture": "available" if _available("screencapture") else "unavailable",
        "edge_tts": "available" if edge else "unavailable",
        "cjk_font": "available" if _cjk_font_available() else "unavailable",
        "selected_voice": DEFAULT_VOICE_ID if edge else "unavailable",
        "selected_voice_rate": DEFAULT_VOICE_RATE if edge else "unavailable",
    }


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

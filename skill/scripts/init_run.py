#!/usr/bin/env python3
"""初始化一次讲解视频运行的输出目录。"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from lib.paths import RunPaths
from lib.run_state import save_run

DEFAULT_VOICE_ID = "zh-CN-YunxiNeural"
DEFAULT_VOICE_RATE = "-3%"

VOICE_STYLES: dict[str, str] = {
    "zh-CN-YunxiNeural": "中文自然男声",
    "zh-CN-XiaoxiaoNeural": "中文自然女声",
    "zh-CN-YunyangNeural": "中文新闻播报男声",
    "zh-CN-XiaoyiNeural": "中文活泼女声",
}


def voice_style_for(voice_id: str) -> str:
    """按 voice_id 返回可读风格标签；未知 ID 回退为该 ID 本身。"""
    return VOICE_STYLES.get(voice_id, voice_id)


def init_run(
    paths: RunPaths,
    *,
    voice_id: str,
    voice_rate: str,
    run_id: str,
    target_description: str = "",
) -> None:
    paths.ensure_dirs()
    save_run(
        paths,
        {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized",
            "voice_provider": "Edge TTS",
            "voice_id": voice_id,
            "voice_rate": voice_rate,
            "voice_style": voice_style_for(voice_id),
            "target_description": target_description,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化讲解视频运行目录")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--voice-id", default=DEFAULT_VOICE_ID)
    parser.add_argument("--voice-rate", default=DEFAULT_VOICE_RATE)
    parser.add_argument("--target-description", default="")
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    init_run(
        paths,
        voice_id=args.voice_id,
        voice_rate=args.voice_rate,
        run_id=paths.root.name,
        target_description=args.target_description,
    )
    print(f"已初始化: {paths.root}")


if __name__ == "__main__":
    main()

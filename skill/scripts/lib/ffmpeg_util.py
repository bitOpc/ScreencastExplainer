"""ffmpeg / ffprobe 工具函数。"""

import shutil
import subprocess
from pathlib import Path


def ffmpeg_path() -> str:
    candidates = [
        "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "ffmpeg",
    ]
    for candidate in candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise FileNotFoundError("未找到 ffmpeg，请运行: brew install ffmpeg")


def ffprobe_path() -> str:
    candidates = [
        "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe",
        "/opt/homebrew/bin/ffprobe",
        "ffprobe",
    ]
    for candidate in candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise FileNotFoundError("未找到 ffprobe，请运行: brew install ffmpeg")


def probe_duration(path: Path) -> float:
    """用 ffprobe 读取媒体文件时长（秒）。"""
    output = subprocess.run(
        [
            ffprobe_path(),
            "-hide_banner",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(output.stdout.strip())


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run([ffmpeg_path(), *args], check=True)

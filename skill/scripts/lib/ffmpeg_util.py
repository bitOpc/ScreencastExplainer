"""ffmpeg / ffprobe 工具函数。"""

import shutil
import subprocess
from pathlib import Path


def ffmpeg_path() -> str:
    candidates = [
        "/opt/homebrew/bin/ffmpeg",
        "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
        "ffmpeg",
    ]
    for candidate in candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise FileNotFoundError("未找到 ffmpeg，请运行: brew install ffmpeg")


def ffprobe_path() -> str:
    candidates = [
        "/opt/homebrew/bin/ffprobe",
        "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe",
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


def _parse_frame_rate(value: str) -> float | None:
    """解析 ffprobe 的 n/d 或小数帧率字符串。"""
    text = value.strip()
    if not text or text in {"N/A", "0/0"}:
        return None
    if "/" in text:
        num_s, den_s = text.split("/", 1)
        num = float(num_s)
        den = float(den_s)
        if den == 0:
            return None
        return num / den
    return float(text)


def probe_frame_rate(path: Path) -> float:
    """用 ffprobe 读取视频有效帧率；优先 avg_frame_rate，否则 r_frame_rate。"""
    output = subprocess.run(
        [
            ffprobe_path(),
            "-hide_banner",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate,r_frame_rate",
            "-of",
            "default=noprint_wrappers=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    avg: float | None = None
    nominal: float | None = None
    for line in output.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        rate = _parse_frame_rate(value)
        if key == "avg_frame_rate":
            avg = rate
        elif key == "r_frame_rate":
            nominal = rate
    chosen = avg if avg and avg > 0 else nominal
    if chosen is None or chosen <= 0:
        raise ValueError(f"无法读取视频帧率: {path}")
    return chosen


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run([ffmpeg_path(), *args], check=True)

#!/usr/bin/env python3
"""录屏导入与音画时长校验。"""

import argparse
import subprocess
import sys
from pathlib import Path

from lib.ffmpeg_util import ffmpeg_path, probe_duration, run_ffmpeg
from lib.paths import RunPaths
from lib.run_state import update_run_status


def validate_av_duration(
    *, video_duration: float, audio_duration: float, tolerance: float = 0.5
) -> None:
    """校验视频与旁白时长是否在允许偏差内。"""
    delta = abs(video_duration - audio_duration)
    if delta > tolerance:
        raise ValueError(
            f"音画时长偏差过大: 视频 {video_duration:.2f}s, 旁白 {audio_duration:.2f}s, "
            f"偏差 {delta:.2f}s（允许 ±{tolerance}s）。请重新录屏或调整旁白后重试。"
        )


def normalize_video(raw_mp4: Path, normalized_mp4: Path) -> None:
    """将 raw.mp4 标准化为 normalized.mp4，优先流复制，失败则重编码。"""
    normalized_mp4.parent.mkdir(parents=True, exist_ok=True)
    copy_args = [
        "-hide_banner",
        "-y",
        "-i",
        str(raw_mp4),
        "-c",
        "copy",
        str(normalized_mp4),
    ]
    try:
        subprocess.run([ffmpeg_path(), *copy_args], check=True)
    except subprocess.CalledProcessError:
        run_ffmpeg(
            [
                "-hide_banner",
                "-y",
                "-i",
                str(raw_mp4),
                "-c:v",
                "libx264",
                str(normalized_mp4),
            ]
        )


def ingest_capture(paths: RunPaths, *, tolerance: float = 0.5) -> None:
    """校验录屏时长并生成 normalized.mp4。"""
    if not paths.raw_mp4.is_file():
        raise FileNotFoundError(f"未找到录屏文件: {paths.raw_mp4}")
    if not paths.narration_wav.is_file():
        raise FileNotFoundError(f"未找到旁白文件: {paths.narration_wav}")

    video_duration = probe_duration(paths.raw_mp4)
    audio_duration = probe_duration(paths.narration_wav)
    validate_av_duration(
        video_duration=video_duration,
        audio_duration=audio_duration,
        tolerance=tolerance,
    )
    normalize_video(paths.raw_mp4, paths.normalized_mp4)
    update_run_status(paths, "ingested")


def main() -> None:
    parser = argparse.ArgumentParser(description="录屏导入与音画时长校验")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="运行输出目录（含 capture/raw.mp4 与 narration.wav）",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.5,
        help="音画时长允许偏差（秒，默认: 0.5）",
    )
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    try:
        ingest_capture(paths, tolerance=args.tolerance)
    except FileNotFoundError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"已导入录屏: {paths.normalized_mp4}")
    print("状态已更新为 ingested")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""硬字幕视频合成：将 normalized 视频、旁白与 ASS 字幕合成为 final.mp4。"""

import argparse
from pathlib import Path

from lib.ffmpeg_util import run_ffmpeg
from lib.paths import RunPaths
from lib.run_state import update_run_status

DEFAULT_CRF = 18


def format_ass_filter(path: Path) -> str:
    """生成 ffmpeg ass 滤镜参数字符串，路径含特殊字符时用单引号转义。"""
    path_str = path.as_posix()
    if any(ch in path_str for ch in " ':,;[]"):
        escaped = path_str.replace("'", "'\\''")
        return f"ass='{escaped}'"
    return f"ass={path_str}"


def build_ass_filter_graph(path: Path) -> str:
    """构建 filter_complex：将视频流经 ass 滤镜烧录字幕后输出 [vout]。"""
    return f"[0:v]{format_ass_filter(path)}[vout]"


def build_mux_command(paths: RunPaths, *, crf: int = DEFAULT_CRF) -> list[str]:
    """构建 ffmpeg 合成命令参数列表（不含 ffmpeg 可执行文件路径）。"""
    paths.video_dir.mkdir(parents=True, exist_ok=True)
    return [
        "-hide_banner",
        "-y",
        "-i",
        str(paths.normalized_mp4),
        "-i",
        str(paths.narration_wav),
        "-filter_complex",
        build_ass_filter_graph(paths.captions_ass),
        "-map",
        "[vout]",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-shortest",
        "-movflags",
        "+faststart",
        str(paths.final_mp4),
    ]


def _ensure_inputs(paths: RunPaths) -> None:
    """检查合成所需输入文件是否存在。"""
    required = [
        ("video/normalized.mp4", paths.normalized_mp4),
        ("narration.wav", paths.narration_wav),
        ("captions.ass", paths.captions_ass),
    ]
    missing = [label for label, path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"缺少合成所需文件: {', '.join(missing)}")


def compose_video(paths: RunPaths, *, crf: int = DEFAULT_CRF) -> Path:
    """将 normalized 视频、旁白与 ASS 字幕合成为 final.mp4。"""
    _ensure_inputs(paths)
    run_ffmpeg(build_mux_command(paths, crf=crf))
    return paths.final_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="硬字幕视频合成")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="运行输出目录（含 normalized.mp4、narration.wav、captions.ass）",
    )
    parser.add_argument(
        "--crf",
        type=int,
        default=DEFAULT_CRF,
        help=f"libx264 质量参数（默认: {DEFAULT_CRF}）",
    )
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    output = compose_video(paths, crf=args.crf)
    update_run_status(paths, "composed")
    print(f"已合成视频: {output}")


if __name__ == "__main__":
    main()

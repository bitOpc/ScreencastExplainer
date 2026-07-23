#!/usr/bin/env python3
"""硬字幕视频合成：将 normalized 视频、旁白与 ASS 字幕合成为 final.mp4。"""

import argparse
import json
from pathlib import Path

from lib.avatar_overlay import build_pip_filter_complex
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


def _resolve_with_avatar(paths: RunPaths, with_avatar: bool | None) -> bool:
    """判断是否启用 avatar 叠加；with_avatar=None 时按 avatar.json 自动探测。"""
    if with_avatar is False:
        return False
    if not paths.avatar_json.is_file() or not paths.avatar_mp4.is_file():
        return False
    if with_avatar is True:
        return True
    try:
        data = json.loads(paths.avatar_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return bool(data.get("use_presenter"))


def build_mux_command(
    paths: RunPaths,
    *,
    crf: int = DEFAULT_CRF,
    with_avatar: bool | None = None,
) -> list[str]:
    """构建 ffmpeg 合成命令参数列表（不含 ffmpeg 可执行文件路径）。"""
    paths.video_dir.mkdir(parents=True, exist_ok=True)
    use_avatar = _resolve_with_avatar(paths, with_avatar)

    encode_args = [
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

    if use_avatar:
        return [
            "-hide_banner",
            "-y",
            "-i",
            str(paths.normalized_mp4),
            "-i",
            str(paths.avatar_mp4),
            "-i",
            str(paths.narration_wav),
            "-filter_complex",
            build_pip_filter_complex(captions_ass=paths.captions_ass),
            "-map",
            "[vout]",
            "-map",
            "2:a:0",
            *encode_args,
        ]

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
        *encode_args,
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


def compose_video(
    paths: RunPaths,
    *,
    crf: int = DEFAULT_CRF,
    with_avatar: bool | None = None,
) -> Path:
    """将 normalized 视频、旁白与 ASS 字幕合成为 final.mp4。"""
    _ensure_inputs(paths)
    run_ffmpeg(build_mux_command(paths, crf=crf, with_avatar=with_avatar))
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
    avatar_group = parser.add_mutually_exclusive_group()
    avatar_group.add_argument(
        "--with-avatar",
        action="store_true",
        default=None,
        help="强制叠加 avatar 画中画",
    )
    avatar_group.add_argument(
        "--no-avatar",
        action="store_false",
        dest="with_avatar",
        help="跳过 avatar 叠加",
    )
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    output = compose_video(paths, crf=args.crf, with_avatar=args.with_avatar)
    update_run_status(paths, "composed")
    print(f"已合成视频: {output}")


if __name__ == "__main__":
    main()

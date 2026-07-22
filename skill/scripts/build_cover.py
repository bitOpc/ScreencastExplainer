#!/usr/bin/env python3
"""根据成片内容与运行元数据生成视频封面。"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from lib.cover import build_cover, load_run_context
from lib.ffmpeg_util import ffprobe_path
from lib.paths import RunPaths
from lib.run_state import load_run, save_run


def _has_audio(path: Path) -> bool:
    result = subprocess.run(
        [
            ffprobe_path(),
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return "audio" in result.stdout


def _pick_video_path(paths: RunPaths, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    if paths.final_mp4.is_file():
        return paths.final_mp4
    if paths.video_dir.is_dir():
        for mp4 in sorted(paths.video_dir.glob("*.mp4")):
            if mp4.name == "normalized.mp4":
                continue
            if _has_audio(mp4):
                return mp4
    if paths.normalized_mp4.is_file():
        return paths.normalized_mp4
    if paths.raw_mp4.is_file():
        return paths.raw_mp4
    raise FileNotFoundError(
        "未找到可用视频源。请先完成 compose 生成带旁白的成片，或通过 --video 指定文件。"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 YouTube 风格视频封面")
    parser.add_argument("--output-dir", type=Path, required=True, help="运行输出目录")
    parser.add_argument("--video", type=Path, help="取帧视频（默认优先 final.mp4）")
    parser.add_argument("--title", help="封面主标题（默认从内容推断）")
    parser.add_argument("--subtitle", help="封面副标题（默认从内容推断）")
    parser.add_argument(
        "--frame-seconds",
        type=float,
        help="取帧时间点（秒，默认根据分段/切换动作推断）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="封面输出路径（默认 <output-dir>/video/cover.png）",
    )
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    video_path = _pick_video_path(paths, args.video.resolve() if args.video else None)
    output_path = (args.output or paths.cover_png).resolve()

    context = load_run_context(paths.root)
    output, cover_text = build_cover(
        video_path=video_path,
        output_path=output_path,
        title=args.title,
        subtitle=args.subtitle,
        frame_seconds=args.frame_seconds,
        **context,
    )

    report = {
        "cover_png": str(output),
        "video_source": str(video_path),
        "title": cover_text.title,
        "subtitle": cover_text.subtitle,
        "frame_seconds": cover_text.frame_seconds,
        "inference_source": cover_text.source,
    }
    report_path = paths.cover_report_json
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if paths.run_json.is_file():
        run_data = load_run(paths)
        run_data["cover_png"] = str(output)
        run_data["cover_title"] = cover_text.title
        run_data["cover_subtitle"] = cover_text.subtitle
        save_run(paths, run_data)

    print(f"已生成封面: {output}")
    print(f"标题: {cover_text.title} / {cover_text.subtitle}")
    print(f"取帧: {cover_text.frame_seconds:.2f}s（{cover_text.source}）")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""按旁白分段调用本地 SadTalker，并拼接讲解人头像视频。"""

import argparse
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from build_narration import DEFAULT_GAP
from lib.ffmpeg_util import run_ffmpeg
from lib.paths import RunPaths
from lib.presenter_config import default_presenter_config, load_presenter_config


def load_run_avatar(paths: RunPaths) -> dict[str, Any]:
    """读取本次运行中用户确认的头像配置。"""
    if not paths.avatar_json.is_file():
        raise ValueError(f"缺少头像配置: {paths.avatar_json}")
    return json.loads(paths.avatar_json.read_text(encoding="utf-8"))


def list_narration_clips(paths: RunPaths) -> list[Path]:
    """返回按编号排序的 Edge TTS WAV 片段。"""
    return sorted((paths.work_audio_dir / "edge_clips").glob("clip_*.wav"))


def run_sadtalker_segment(
    *,
    python: Path,
    sadtalker_root: Path,
    source_image: Path,
    audio: Path,
    out_mp4: Path,
    still: bool,
    preprocess: str,
    face_model_resolution: int,
    cpu: bool = False,
) -> None:
    """为单段音频生成无音轨 SadTalker 视频。"""
    result_dir = out_mp4.parent / f"{out_mp4.stem}_sadtalker_result"
    result_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(python),
        str(sadtalker_root / "inference.py"),
        "--driven_audio",
        str(audio),
        "--source_image",
        str(source_image),
        "--result_dir",
        str(result_dir),
        "--preprocess",
        preprocess,
        "--size",
        str(face_model_resolution),
    ]
    if still:
        command.append("--still")
    if cpu:
        command.append("--cpu")
    subprocess.run(command, check=True)

    candidates = list(result_dir.rglob("*.mp4"))
    if not candidates:
        raise FileNotFoundError(f"SadTalker 未在 {result_dir} 生成 MP4")
    generated = max(candidates, key=lambda path: path.stat().st_mtime)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-hide_banner",
            "-y",
            "-i",
            str(generated),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "copy",
            str(out_mp4),
        ]
    )


def concat_avatar_clips(
    clip_mp4s: list[Path], gap_seconds: float, output: Path
) -> None:
    """在片段之间插入上一段末帧，并将结果拼接为无音轨 MP4。"""
    if not clip_mp4s:
        raise ValueError("没有可拼接的头像视频片段")

    output.parent.mkdir(parents=True, exist_ok=True)
    entries: list[Path] = [clip_mp4s[0]]
    gap_dir = output.parent / "avatar_gaps"
    for index, clip in enumerate(clip_mp4s[:-1], start=1):
        frame = gap_dir / f"gap_{index:03d}.png"
        gap_video = gap_dir / f"gap_{index:03d}.mp4"
        frame.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg(
            [
                "-hide_banner",
                "-y",
                "-sseof",
                "-0.1",
                "-i",
                str(clip),
                "-frames:v",
                "1",
                str(frame),
            ]
        )
        run_ffmpeg(
            [
                "-hide_banner",
                "-y",
                "-loop",
                "1",
                "-i",
                str(frame),
                "-t",
                str(gap_seconds),
                "-an",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(gap_video),
            ]
        )
        entries.extend((gap_video, clip_mp4s[index]))

    concat_list = output.parent / "avatar_concat.txt"
    concat_list.write_text(
        "\n".join(f"file '{entry.as_posix()}'" for entry in entries) + "\n",
        encoding="utf-8",
    )
    run_ffmpeg(
        [
            "-hide_banner",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ]
    )


def _presenter_config(presenter_cfg: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_presenter_config()
    config = load_presenter_config() if presenter_cfg is None else presenter_cfg
    defaults.update(config)
    defaults["sadtalker"].update(config.get("sadtalker", {}))
    return defaults


def _write_report(paths: RunPaths, segments: list[dict[str, Any]]) -> None:
    paths.avatar_report_json.parent.mkdir(parents=True, exist_ok=True)
    paths.avatar_report_json.write_text(
        json.dumps(
            {"segments": segments, "output": str(paths.avatar_mp4)},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_avatar(
    paths: RunPaths, *, presenter_cfg: dict[str, Any] | None = None
) -> Path:
    """基于当前 run 的已确认头像和旁白片段生成 avatar.mp4。"""
    avatar = load_run_avatar(paths)
    if avatar.get("use_presenter") is not True:
        raise ValueError("avatar.json 的 use_presenter 必须为 true")
    source_image = Path(avatar.get("source_image", "")).expanduser()
    if not source_image.is_file():
        raise ValueError(f"头像源图片不存在: {source_image}")

    clips = list_narration_clips(paths)
    if not clips:
        raise ValueError("没有可用的旁白片段")

    config = _presenter_config(presenter_cfg)
    sadtalker_root = Path(config["sadtalker_root"]).expanduser()
    python = sadtalker_root / "venv" / "bin" / "python"
    sadtalker = config["sadtalker"]
    clip_mp4s: list[Path] = []
    report_segments: list[dict[str, Any]] = []

    for index, audio in enumerate(clips, start=1):
        out_mp4 = paths.video_dir / "avatar_segments" / f"clip_{index:03d}.mp4"
        started_at = time.monotonic()
        try:
            run_sadtalker_segment(
                python=python,
                sadtalker_root=sadtalker_root,
                source_image=source_image,
                audio=audio,
                out_mp4=out_mp4,
                still=bool(sadtalker["still"]),
                preprocess=str(sadtalker["preprocess"]),
                face_model_resolution=int(sadtalker["face_model_resolution"]),
                cpu=not bool(config["has_cuda"]),
            )
        except Exception as error:
            report_segments.append(
                {
                    "id": index,
                    "status": "failed",
                    "seconds": time.monotonic() - started_at,
                }
            )
            _write_report(paths, report_segments)
            raise RuntimeError(f"SadTalker 生成第 {index} 段失败") from error

        clip_mp4s.append(out_mp4)
        report_segments.append(
            {"id": index, "status": "ok", "seconds": time.monotonic() - started_at}
        )

    try:
        concat_avatar_clips(clip_mp4s, DEFAULT_GAP, paths.avatar_mp4)
    finally:
        _write_report(paths, report_segments)
    return paths.avatar_mp4


def main() -> None:
    parser = argparse.ArgumentParser(description="为本次运行生成讲解人头像视频")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="运行输出目录（含 avatar.json 与 workaudio/edge_clips）",
    )
    args = parser.parse_args()
    output = build_avatar(RunPaths(args.output_dir.resolve()))
    print(f"已生成讲解人头像视频: {output}")


if __name__ == "__main__":
    main()

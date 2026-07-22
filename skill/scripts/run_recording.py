#!/usr/bin/env python3
"""同时运行单窗口录屏与通用 UI 动作时间轴。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys

# 保证可导入同目录 lib
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from ingest_capture import validate_av_duration  # noqa: E402
from lib.ffmpeg_util import probe_duration  # noqa: E402
from lib.paths import RunPaths  # noqa: E402

DEFAULT_AV_TOLERANCE = 0.5


def build_record_window_command(
    *,
    python_executable: str,
    scripts_dir: Path,
    output_dir: Path,
    window_id: int,
) -> list[str]:
    return [
        python_executable,
        str(scripts_dir / "record_window.py"),
        "--output-dir",
        str(output_dir),
        "--window-id",
        str(window_id),
    ]


def build_timeline_player_command(
    *,
    python_executable: str,
    scripts_dir: Path,
    actions_path: Path,
    output_dir: Path,
    dry_run: bool = False,
    allow_foreground: bool = False,
) -> list[str]:
    command = [
        python_executable,
        str(scripts_dir / "timeline_player.py"),
        "--actions",
        str(actions_path),
        "--output-dir",
        str(output_dir),
    ]
    if dry_run:
        command.append("--dry-run")
    if allow_foreground:
        command.append("--allow-foreground")
    return command


def validate_recording_output(
    paths: RunPaths,
    *,
    tolerance: float = DEFAULT_AV_TOLERANCE,
) -> dict[str, float]:
    """录屏结束后校验 raw.mp4 与 narration.wav 时长。"""
    if not paths.raw_mp4.exists():
        raise FileNotFoundError(f"录屏未生成文件: {paths.raw_mp4}")
    if paths.raw_mp4.stat().st_size == 0:
        raise RuntimeError(f"录屏文件为空: {paths.raw_mp4}")

    video_duration = probe_duration(paths.raw_mp4)
    audio_duration = probe_duration(paths.narration_wav)
    validate_av_duration(
        video_duration=video_duration,
        audio_duration=audio_duration,
        tolerance=tolerance,
    )
    return {
        "video_duration": video_duration,
        "audio_duration": audio_duration,
    }


def write_recording_report(
    paths: RunPaths,
    *,
    status: str,
    window_id: int,
    player_returncode: int,
    recorder_returncode: int | None,
    durations: dict[str, float] | None = None,
    error: str | None = None,
) -> Path:
    report = {
        "status": status,
        "window_id": window_id,
        "player_returncode": player_returncode,
        "recorder_returncode": recorder_returncode,
        "raw_mp4": str(paths.raw_mp4),
        "narration_wav": str(paths.narration_wav),
    }
    if durations:
        report.update(durations)
    if error:
        report["error"] = error
    report_path = paths.root / "capture" / "recording.report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def run_recording(
    *,
    output_dir: Path,
    window_id: int,
    actions_path: Path | None = None,
    dry_run: bool = False,
    allow_foreground: bool = False,
    av_tolerance: float = DEFAULT_AV_TOLERANCE,
) -> int:
    scripts_dir = Path(__file__).resolve().parent
    python_executable = sys.executable
    paths = RunPaths(output_dir)
    actions = actions_path or paths.actions_json
    if not actions.exists():
        raise FileNotFoundError(f"未找到 actions.json: {actions}")

    timeline_command = build_timeline_player_command(
        python_executable=python_executable,
        scripts_dir=scripts_dir,
        actions_path=actions,
        output_dir=output_dir,
        dry_run=dry_run,
        allow_foreground=allow_foreground,
    )
    if dry_run:
        return subprocess.run(timeline_command, check=False).returncode

    if not paths.narration_wav.exists():
        raise FileNotFoundError(
            f"未找到旁白文件: {paths.narration_wav}。请先运行 build_narration.py。"
        )

    record_command = build_record_window_command(
        python_executable=python_executable,
        scripts_dir=scripts_dir,
        output_dir=output_dir,
        window_id=window_id,
    )
    recorder = subprocess.Popen(record_command)
    player_returncode = 1
    recorder_returncode: int | None = None
    try:
        player = subprocess.run(timeline_command, check=False)
        player_returncode = player.returncode
        # 必须等 screencapture 自然结束；禁止 timeline 结束后 terminate 录屏进程。
        recorder_returncode = recorder.wait()
    except Exception as exc:
        write_recording_report(
            paths,
            status="failed",
            window_id=window_id,
            player_returncode=player_returncode,
            recorder_returncode=recorder_returncode,
            error=str(exc),
        )
        if recorder.poll() is None:
            recorder.kill()
            recorder.wait(timeout=5)
        raise

    try:
        durations = validate_recording_output(paths, tolerance=av_tolerance)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        write_recording_report(
            paths,
            status="failed",
            window_id=window_id,
            player_returncode=player_returncode,
            recorder_returncode=recorder_returncode,
            error=str(exc),
        )
        if player_returncode != 0:
            return player_returncode
        return 1

    write_recording_report(
        paths,
        status="ok",
        window_id=window_id,
        player_returncode=player_returncode,
        recorder_returncode=recorder_returncode,
        durations=durations,
    )
    if player_returncode != 0:
        return player_returncode
    return recorder_returncode or 0


def main() -> None:
    parser = argparse.ArgumentParser(description="单窗口录屏 + actions.json 时间轴回放")
    parser.add_argument("--output-dir", type=Path, required=True, help="运行输出目录")
    parser.add_argument("--window-id", type=int, required=True, help="目标录屏窗口 ID")
    parser.add_argument("--actions", type=Path, help="actions.json 路径（默认 <output-dir>/actions.json）")
    parser.add_argument("--dry-run", action="store_true", help="只校验/预览动作时间轴，不录屏")
    parser.add_argument("--allow-foreground", action="store_true", help="允许 foreground 动作")
    parser.add_argument(
        "--av-tolerance",
        type=float,
        default=DEFAULT_AV_TOLERANCE,
        help=f"录屏结束后与 narration.wav 的允许时长偏差（秒，默认 {DEFAULT_AV_TOLERANCE}）",
    )
    args = parser.parse_args()

    raise SystemExit(
        run_recording(
            output_dir=args.output_dir,
            window_id=args.window_id,
            actions_path=args.actions,
            dry_run=args.dry_run,
            allow_foreground=args.allow_foreground,
            av_tolerance=args.av_tolerance,
        )
    )


if __name__ == "__main__":
    main()

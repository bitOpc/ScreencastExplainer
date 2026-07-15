#!/usr/bin/env python3
"""同时运行单窗口录屏与通用 UI 动作时间轴。"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

# 保证可导入同目录 lib
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.paths import RunPaths  # noqa: E402


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


def run_recording(
    *,
    output_dir: Path,
    window_id: int,
    actions_path: Path | None = None,
    dry_run: bool = False,
    allow_foreground: bool = False,
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

    record_command = build_record_window_command(
        python_executable=python_executable,
        scripts_dir=scripts_dir,
        output_dir=output_dir,
        window_id=window_id,
    )
    recorder = subprocess.Popen(record_command)
    try:
        player = subprocess.run(timeline_command, check=False)
        recorder_return = recorder.wait()
    finally:
        if recorder.poll() is None:
            recorder.terminate()
            recorder.wait(timeout=5)
    if player.returncode != 0:
        return player.returncode
    return recorder_return


def main() -> None:
    parser = argparse.ArgumentParser(description="单窗口录屏 + actions.json 时间轴回放")
    parser.add_argument("--output-dir", type=Path, required=True, help="运行输出目录")
    parser.add_argument("--window-id", type=int, required=True, help="目标录屏窗口 ID")
    parser.add_argument("--actions", type=Path, help="actions.json 路径（默认 <output-dir>/actions.json）")
    parser.add_argument("--dry-run", action="store_true", help="只校验/预览动作时间轴，不录屏")
    parser.add_argument("--allow-foreground", action="store_true", help="允许 foreground 动作")
    args = parser.parse_args()

    raise SystemExit(
        run_recording(
            output_dir=args.output_dir,
            window_id=args.window_id,
            actions_path=args.actions,
            dry_run=args.dry_run,
            allow_foreground=args.allow_foreground,
        )
    )


if __name__ == "__main__":
    main()

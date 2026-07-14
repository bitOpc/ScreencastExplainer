#!/usr/bin/env python3
"""单应用窗口实时录屏（macOS screencapture -v -l）。

使用系统自带 ScreencaptureKit 入口，录制指定 window_id 的连续视频，
而非整屏或截图拼凑。可与 Computer Use / cua-driver 后台操作并行：
录制过程中不必激活目标窗口到前台。
"""

from __future__ import annotations

import argparse
import math
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# 保证可导入同目录 lib
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.ffmpeg_util import probe_duration  # noqa: E402
from lib.paths import RunPaths  # noqa: E402


def build_screencapture_command(
    *,
    window_id: int,
    duration_seconds: float,
    output: Path,
) -> list[str]:
    """构造 screencapture 命令。

    -V 使用向上取整的整数秒，避免旁白尾部被裁切。
    """
    if duration_seconds <= 0:
        raise ValueError(f"录制时长必须大于 0，收到: {duration_seconds}")
    seconds = max(1, int(math.ceil(duration_seconds)))
    binary = shutil.which("screencapture")
    if not binary:
        raise FileNotFoundError(
            "未找到 screencapture。本技能仅支持 macOS 系统自带录屏工具。"
        )
    return [
        binary,
        "-x",  # 静音提示音
        "-v",  # 视频模式
        f"-V{seconds}",
        f"-l{window_id}",
        str(output),
    ]


def resolve_duration(
    *,
    duration: float | None,
    output_dir: Path | None,
) -> float:
    """优先使用显式 --duration；否则从 output-dir 旁白探测。"""
    if duration is not None:
        return float(duration)
    if output_dir is None:
        raise ValueError("未指定 --duration 时必须提供 --output-dir，以读取 narration.wav 时长")
    paths = RunPaths(output_dir)
    if not paths.narration_wav.exists():
        raise FileNotFoundError(
            f"未找到旁白文件: {paths.narration_wav}。"
            "请先运行 build_narration.py，或显式传入 --duration。"
        )
    return probe_duration(paths.narration_wav)


def resolve_output(*, output: Path | None, output_dir: Path | None) -> Path:
    if output is not None:
        return output
    if output_dir is None:
        raise ValueError("必须指定 --output 或 --output-dir")
    return RunPaths(output_dir).raw_mp4


def record_window(
    *,
    window_id: int,
    duration_seconds: float,
    output: Path,
) -> Path:
    """执行单窗口录屏，成功后返回输出路径。"""
    if platform.system() != "Darwin":
        raise RuntimeError("record_window.py 仅支持 macOS")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    command = build_screencapture_command(
        window_id=window_id,
        duration_seconds=duration_seconds,
        output=output,
    )
    print(" ".join(command), flush=True)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"screencapture 失败（退出码 {result.returncode}）。"
            "请确认：1) 已授予「屏幕录制」权限给当前终端/Cursor/Hermes；"
            f"2) window_id={window_id} 仍有效；3) 目标窗口未被销毁。"
        )
    if not output.exists() or output.stat().st_size == 0:
        raise RuntimeError(
            f"录屏未生成有效文件: {output}。"
            "请检查屏幕录制权限与 window_id。"
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="录制单个 macOS 应用窗口（screencapture -v -l），输出到 capture/raw.mp4"
    )
    parser.add_argument(
        "--window-id",
        type=int,
        required=True,
        help="目标窗口 ID（可用 Computer Use / cua-driver list_windows 获取）",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="录制秒数；省略时从 --output-dir/narration.wav 读取",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="运行目录；可自动推断旁白时长与 raw.mp4 路径",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出 mp4 路径（默认 <output-dir>/capture/raw.mp4）",
    )
    args = parser.parse_args()

    try:
        output_dir = args.output_dir.resolve() if args.output_dir else None
        duration = resolve_duration(duration=args.duration, output_dir=output_dir)
        output = resolve_output(
            output=args.output.resolve() if args.output else None,
            output_dir=output_dir,
        )
        path = record_window(
            window_id=args.window_id,
            duration_seconds=duration,
            output=output,
        )
    except (ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        sys.exit(1)

    print(path)


if __name__ == "__main__":
    main()

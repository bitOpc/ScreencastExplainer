import math
import shutil
import subprocess
from pathlib import Path

import pytest

from lib.avatar_overlay import (
    DEFAULT_MIN_PIP_FPS,
    build_pip_filter_complex,
    resolve_pip_output_fps,
)


def _has_ffmpeg_ass_filter() -> bool:
    """返回本机 ffmpeg 是否可执行且包含 ass 滤镜。"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return False
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and " ass " in result.stdout


@pytest.mark.parametrize(
    ("main_fps", "expected"),
    [
        (None, DEFAULT_MIN_PIP_FPS),
        (0, DEFAULT_MIN_PIP_FPS),
        (6.0, DEFAULT_MIN_PIP_FPS),
        (24.4, DEFAULT_MIN_PIP_FPS),
        (25.0, 25),
        (37.3, 37),
        (59.94, 60),
    ],
)
def test_resolve_pip_output_fps(main_fps, expected):
    assert resolve_pip_output_fps(main_fps) == expected


def test_pip_filter_scales_against_main_video_and_contains_circle():
    ass = Path("/tmp/captions.ass")
    graph = build_pip_filter_complex(
        captions_ass=ass, size_ratio=0.18, margin_px=24, fps=25
    )

    assert "ass=" in graph or "ass='" in graph
    assert "scale2ref" in graph
    assert "rh*0.18" in graph
    assert "overlay=" in graph
    assert "[vout]" in graph
    assert "fps=25" in graph
    assert "geq=" in graph or "alphamerge" in graph or "geq" in graph


@pytest.mark.skipif(
    not _has_ffmpeg_ass_filter(), reason="需要带 ass 滤镜的 ffmpeg"
)
def test_pip_filter_renders_placeholder_videos(tmp_path):
    ass = tmp_path / "captions.ass"
    ass.write_text(
        """[Script Info]
ScriptType: v4.00+

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,Arial,24,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,Smoke test
""",
        encoding="utf-8",
    )
    output = tmp_path / "pip-smoke.mp4"
    # 主画面故意用 6fps，验证合成后抬到 25fps（避免口型被抽稀）。
    graph = build_pip_filter_complex(captions_ass=ass, fps=25)

    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-r",
            "6",
            "-i",
            "color=c=blue:s=640x360:d=2",
            "-f",
            "lavfi",
            "-r",
            "25",
            "-i",
            "color=c=yellow:s=320x320:d=2",
            "-filter_complex",
            graph,
            "-map",
            "[vout]",
            "-r",
            "25",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(output),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.is_file()
    assert output.stat().st_size > 0

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=avg_frame_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    rate_text = probe.stdout.strip()
    if "/" in rate_text:
        num, den = rate_text.split("/", 1)
        avg_fps = float(num) / float(den)
    else:
        avg_fps = float(rate_text)
    assert math.isclose(avg_fps, 25.0, rel_tol=0.05)

import shutil
import subprocess
from pathlib import Path

import pytest

from lib.avatar_overlay import build_pip_filter_complex


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


def test_pip_filter_scales_against_main_video_and_contains_circle():
    ass = Path("/tmp/captions.ass")
    graph = build_pip_filter_complex(captions_ass=ass, width_ratio=0.18, margin_px=24)

    assert "ass=" in graph or "ass='" in graph
    assert "scale2ref" in graph
    assert "main_w*0.18" in graph
    assert "overlay=" in graph
    assert "[vout]" in graph
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
    graph = build_pip_filter_complex(captions_ass=ass)

    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=blue:s=640x360:d=2",
            "-f",
            "lavfi",
            "-i",
            "color=c=yellow:s=320x320:d=2",
            "-filter_complex",
            graph,
            "-map",
            "[vout]",
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

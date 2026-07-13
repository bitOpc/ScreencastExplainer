"""compose_video.py 单元测试。"""

from unittest.mock import patch

import pytest

from compose_video import (
    build_ass_filter_graph,
    build_mux_command,
    compose_video,
    format_ass_filter,
)
from lib.paths import RunPaths
from lib.run_state import load_run, save_run


def test_build_mux_command(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.normalized_mp4.write_bytes(b"x")
    paths.narration_wav.write_bytes(b"x")
    paths.captions_ass.write_bytes(b"x")

    cmd = build_mux_command(paths, crf=18)

    assert "-filter_complex" in cmd
    assert build_ass_filter_graph(paths.captions_ass) in cmd
    assert "[vout]" in cmd
    assert str(paths.normalized_mp4) in cmd
    assert str(paths.narration_wav) in cmd
    assert str(paths.final_mp4) in cmd
    assert "-crf" in cmd
    assert cmd[cmd.index("-crf") + 1] == "18"
    assert "-map" in cmd
    assert "1:a:0" in cmd


def test_format_ass_filter_quotes_special_chars(tmp_path):
    ass_path = tmp_path / "captions with spaces.ass"
    assert format_ass_filter(ass_path) == f"ass='{ass_path.as_posix()}'"


def test_compose_video_runs_ffmpeg_and_updates_status(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.normalized_mp4.write_bytes(b"x")
    paths.narration_wav.write_bytes(b"x")
    paths.captions_ass.write_bytes(b"x")
    save_run(paths, {"run_id": "test-run", "status": "ingested"})

    with patch("compose_video.run_ffmpeg") as mock_ffmpeg:
        output = compose_video(paths, crf=18)

    mock_ffmpeg.assert_called_once_with(build_mux_command(paths, crf=18))
    assert output == paths.final_mp4


def test_compose_video_missing_inputs(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)

    with pytest.raises(FileNotFoundError, match="缺少合成所需文件"):
        compose_video(paths)


def test_main_updates_run_status(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.normalized_mp4.write_bytes(b"x")
    paths.narration_wav.write_bytes(b"x")
    paths.captions_ass.write_bytes(b"x")
    save_run(paths, {"run_id": "test-run", "status": "ingested"})

    with patch("compose_video.run_ffmpeg"):
        with patch(
            "sys.argv",
            ["compose_video.py", "--output-dir", str(tmp_run_dir), "--crf", "18"],
        ):
            from compose_video import main

            main()

    assert load_run(paths)["status"] == "composed"

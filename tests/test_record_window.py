"""record_window.py 单元测试（不实际调用 screencapture）。"""

from pathlib import Path

import pytest

from record_window import (
    build_screencapture_command,
    resolve_duration,
    resolve_output,
)


def test_build_screencapture_command_ceils_duration():
    cmd = build_screencapture_command(
        window_id=4261,
        duration_seconds=12.1,
        output=Path("/tmp/raw.mp4"),
    )
    assert cmd[0].endswith("screencapture") or cmd[0] == "screencapture"
    assert "-x" in cmd
    assert "-v" in cmd
    assert "-V13" in cmd  # ceil(12.1) == 13
    assert "-l4261" in cmd
    assert cmd[-1] == "/tmp/raw.mp4"


def test_build_screencapture_command_rejects_nonpositive():
    with pytest.raises(ValueError, match="录制时长"):
        build_screencapture_command(
            window_id=1,
            duration_seconds=0,
            output=Path("/tmp/a.mp4"),
        )


def test_resolve_output_from_output_dir(tmp_run_dir):
    path = resolve_output(output=None, output_dir=tmp_run_dir)
    assert path == tmp_run_dir / "capture" / "raw.mp4"


def test_resolve_duration_requires_output_dir_when_missing():
    with pytest.raises(ValueError, match="--output-dir"):
        resolve_duration(duration=None, output_dir=None)

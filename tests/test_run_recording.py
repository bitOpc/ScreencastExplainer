"""run_recording.py 单元测试。"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from run_recording import (
    build_record_window_command,
    build_timeline_player_command,
    run_recording,
    validate_recording_output,
)
from lib.paths import RunPaths


def test_build_record_window_command_uses_same_python_and_window_id(tmp_path):
    command = build_record_window_command(
        python_executable="/venv/bin/python",
        scripts_dir=Path("/repo/skill/scripts"),
        output_dir=tmp_path,
        window_id=4261,
    )

    assert command == [
        "/venv/bin/python",
        "/repo/skill/scripts/record_window.py",
        "--output-dir",
        str(tmp_path),
        "--window-id",
        "4261",
    ]


def test_build_timeline_player_command_points_to_actions_file(tmp_path):
    actions = tmp_path / "actions.json"
    command = build_timeline_player_command(
        python_executable="/venv/bin/python",
        scripts_dir=Path("/repo/skill/scripts"),
        actions_path=actions,
        output_dir=tmp_path,
        dry_run=True,
    )

    assert command == [
        "/venv/bin/python",
        "/repo/skill/scripts/timeline_player.py",
        "--actions",
        str(actions),
        "--output-dir",
        str(tmp_path),
        "--dry-run",
    ]


def _write_minimal_run_dir(run_dir: Path) -> None:
    run_dir.mkdir()
    (run_dir / "capture").mkdir()
    (run_dir / "actions.json").write_text('{"version": 1, "events": []}', encoding="utf-8")
    (run_dir / "narration.wav").write_bytes(b"wav")
    (run_dir / "capture" / "raw.mp4").write_bytes(b"mp4")


def test_validate_recording_output_ok(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run_dir(run_dir)

    with patch("run_recording.probe_duration", side_effect=[60.0, 60.2]):
        result = validate_recording_output(RunPaths(run_dir))

    assert result == {"video_duration": 60.0, "audio_duration": 60.2}


def test_validate_recording_output_raises_on_mismatch(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run_dir(run_dir)

    with patch("run_recording.probe_duration", side_effect=[50.0, 60.0]):
        with pytest.raises(ValueError, match="音画时长偏差"):
            validate_recording_output(RunPaths(run_dir))


def test_validate_recording_output_raises_on_missing_raw(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "narration.wav").write_bytes(b"wav")

    with pytest.raises(FileNotFoundError, match="录屏未生成"):
        validate_recording_output(RunPaths(run_dir))


def test_run_recording_waits_for_recorder_without_terminate(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run_dir(run_dir)

    mock_recorder = MagicMock()
    mock_recorder.wait.return_value = 0

    with patch("run_recording.subprocess.Popen", return_value=mock_recorder):
        with patch("run_recording.subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("run_recording.probe_duration", side_effect=[60.0, 60.1]):
                rc = run_recording(output_dir=run_dir, window_id=42)

    mock_recorder.wait.assert_called_once()
    mock_recorder.terminate.assert_not_called()
    mock_recorder.kill.assert_not_called()
    assert rc == 0

    report = (run_dir / "capture" / "recording.report.json").read_text(encoding="utf-8")
    assert '"status": "ok"' in report
    assert '"video_duration": 60.0' in report


def test_run_recording_fails_on_duration_mismatch(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run_dir(run_dir)

    mock_recorder = MagicMock()
    mock_recorder.wait.return_value = 0

    with patch("run_recording.subprocess.Popen", return_value=mock_recorder):
        with patch("run_recording.subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("run_recording.probe_duration", side_effect=[59.0, 424.0]):
                rc = run_recording(output_dir=run_dir, window_id=42)

    assert rc == 1
    report = (run_dir / "capture" / "recording.report.json").read_text(encoding="utf-8")
    assert '"status": "failed"' in report
    assert "音画时长偏差" in report


def test_run_recording_dry_run_skips_recorder(tmp_path):
    run_dir = tmp_path / "run"
    _write_minimal_run_dir(run_dir)

    with patch("run_recording.subprocess.Popen") as popen:
        with patch("run_recording.subprocess.run", return_value=MagicMock(returncode=0)) as run:
            rc = run_recording(output_dir=run_dir, window_id=42, dry_run=True)

    popen.assert_not_called()
    run.assert_called_once()
    assert rc == 0

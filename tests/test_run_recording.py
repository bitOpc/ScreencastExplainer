from pathlib import Path

from run_recording import build_record_window_command, build_timeline_player_command


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

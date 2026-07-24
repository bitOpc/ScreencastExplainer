from pathlib import Path

from lib.paths import RunPaths


def test_run_paths_resolve(tmp_path: Path):
    run_dir = tmp_path / "demo-run"
    paths = RunPaths(run_dir)
    assert paths.run_json == run_dir / "run.json"
    assert paths.segments_json == run_dir / "segments.json"
    assert paths.narration_wav == run_dir / "narration.wav"
    assert paths.raw_mp4 == run_dir / "capture" / "raw.mp4"
    assert paths.normalized_mp4 == run_dir / "video" / "normalized.mp4"
    assert paths.final_mp4 == run_dir / "video" / "final.mp4"
    assert paths.cover_png == run_dir / "video" / "cover.png"
    assert paths.cover_report_json == run_dir / "video" / "cover.report.json"


def test_avatar_paths(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    assert paths.avatar_json == tmp_run_dir / "avatar.json"
    assert paths.avatar_mp4 == tmp_run_dir / "video" / "avatar.mp4"
    assert paths.avatar_report_json == tmp_run_dir / "video" / "avatar.report.json"
    assert paths.avatar_framing_dir == tmp_run_dir / "avatar_framing"

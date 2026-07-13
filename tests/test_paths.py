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

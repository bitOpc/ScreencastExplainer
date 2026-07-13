import json

from lib.paths import RunPaths
from lib.run_state import load_segments, save_run, save_segments


def test_save_and_load_segments(tmp_run_dir, sample_segments_draft):
    paths = RunPaths(tmp_run_dir)
    save_segments(paths, sample_segments_draft)
    loaded = load_segments(paths)
    assert loaded["status"] == "draft"
    assert len(loaded["segments"]) == 2


def test_save_run(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    save_run(paths, {"run_id": "demo", "status": "initialized"})
    data = json.loads(paths.run_json.read_text(encoding="utf-8"))
    assert data["run_id"] == "demo"

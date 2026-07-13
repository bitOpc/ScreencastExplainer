import json
from datetime import datetime

from init_run import init_run
from lib.paths import RunPaths


def test_init_run_creates_structure(tmp_path):
    run_dir = tmp_path / "20260713-demo"
    init_run(
        RunPaths(run_dir),
        voice_id="zh-CN-YunxiNeural",
        voice_rate="-3%",
        run_id="20260713-demo",
    )
    paths = RunPaths(run_dir)
    assert paths.capture_dir.is_dir()
    assert paths.video_dir.is_dir()
    data = json.loads(paths.run_json.read_text(encoding="utf-8"))
    assert data["status"] == "initialized"
    assert data["voice_id"] == "zh-CN-YunxiNeural"

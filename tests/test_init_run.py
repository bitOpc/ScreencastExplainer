import json
from datetime import datetime

from init_run import init_run, voice_style_for
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
    assert data["voice_style"] == "中文自然男声"


def test_voice_style_follows_voice_id(tmp_path):
    run_dir = tmp_path / "xiaoxiao-demo"
    init_run(
        RunPaths(run_dir),
        voice_id="zh-CN-XiaoxiaoNeural",
        voice_rate="-3%",
        run_id="xiaoxiao-demo",
    )
    data = json.loads(RunPaths(run_dir).run_json.read_text(encoding="utf-8"))
    assert data["voice_id"] == "zh-CN-XiaoxiaoNeural"
    assert data["voice_style"] == "中文自然女声"
    assert voice_style_for("zh-CN-YunyangNeural") == "中文新闻播报男声"
    assert voice_style_for("custom-voice") == "custom-voice"

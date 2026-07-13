"""build_narration.py 单元测试。"""

from unittest.mock import AsyncMock, patch

import pytest

from build_narration import build_narration
from lib.paths import RunPaths
from lib.run_state import load_segments, save_run, save_segments


@pytest.mark.asyncio
async def test_build_narration_updates_segments(tmp_run_dir, sample_segments_draft):
    paths = RunPaths(tmp_run_dir)
    save_segments(paths, sample_segments_draft)
    save_run(paths, {"run_id": "test-run", "status": "initialized"})

    async def fake_synthesize(text, output, voice, rate):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\x00")

    with patch("build_narration.synthesize_clip", new=AsyncMock(side_effect=fake_synthesize)):
        with patch("build_narration.run_ffmpeg"):
            with patch("build_narration.wav_duration", return_value=3.0):
                timings = await build_narration(
                    paths, voice_id="zh-CN-YunxiNeural", voice_rate="-3%", gap=0.45
                )

    assert len(timings) == 2
    data = load_segments(paths)
    assert data["status"] == "narrated"
    assert "start" in data["segments"][0]
    assert "end" in data["segments"][0]
    assert data["segments"][0]["actual_duration"] == 3.0
    assert data["segments"][0]["start"] == "00:00:00,000"
    assert data["segments"][0]["end"] == "00:00:03,000"
    assert data["segments"][1]["start"] == "00:00:03,450"
    assert data["segments"][1]["end"] == "00:00:06,450"
    assert paths.captions_srt.exists()
    assert paths.captions_ass.exists()

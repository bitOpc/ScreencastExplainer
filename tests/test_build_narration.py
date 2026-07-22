"""build_narration.py 单元测试。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from build_narration import build_concat_list, build_narration
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
            with patch("build_narration.write_silence_wav"):
                with patch("build_narration.wav_duration", return_value=3.0):
                    timings, cues = await build_narration(
                        paths, voice_id="zh-CN-YunxiNeural", voice_rate="-3%", gap=0.45
                    )

    assert len(timings) == 2
    assert len(cues) >= 2
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


@pytest.mark.asyncio
async def test_build_narration_keeps_actual_duration_when_longer_than_expected(
    tmp_run_dir, sample_segments_draft
):
    """TTS 超出 expected_duration 时不得加速，时间轴与拼接列表以实际时长为准。"""
    paths = RunPaths(tmp_run_dir)
    save_segments(paths, sample_segments_draft)
    save_run(paths, {"run_id": "test-run", "status": "initialized"})

    # segment0 expected=3, segment1 expected=4；实际都更长
    durations = iter([30.5, 24.2])

    async def fake_synthesize(text, output, voice, rate):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"\x00")

    ffmpeg_calls: list[list[str]] = []

    def capture_ffmpeg(args):
        ffmpeg_calls.append(list(args))

    with patch("build_narration.synthesize_clip", new=AsyncMock(side_effect=fake_synthesize)):
        with patch("build_narration.run_ffmpeg", side_effect=capture_ffmpeg):
            with patch("build_narration.write_silence_wav", MagicMock()):
                with patch(
                    "build_narration.wav_duration", side_effect=lambda _p: next(durations)
                ):
                    await build_narration(
                        paths, voice_id="zh-CN-YunxiNeural", voice_rate="-3%", gap=0.45
                    )

    data = load_segments(paths)
    assert data["segments"][0]["actual_duration"] == 30.5
    assert data["segments"][0]["end"] == "00:00:30,500"
    assert data["segments"][1]["start"] == "00:00:30,950"
    assert data["segments"][1]["actual_duration"] == 24.2
    assert data["segments"][1]["end"] == "00:00:55,150"

    # 不得使用 atempo 加速
    flat = " ".join(" ".join(c) for c in ffmpeg_calls)
    assert "atempo=" not in flat

    concat_list = (paths.work_audio_dir / "edge_concat.txt").read_text(encoding="utf-8")
    assert "clip_001.wav" in concat_list
    assert "clip_002.wav" in concat_list
    assert "silence_gap.wav" in concat_list
    # 拼接用原始 clip，不是 padded/加速后的文件
    assert "padded_" not in concat_list


def test_build_concat_list_interleaves_silence_gaps(tmp_path):
    clips = [tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "c.wav"]
    silence = tmp_path / "silence_gap.wav"
    entries = build_concat_list(clips, silence)
    assert entries == [
        tmp_path / "a.wav",
        silence,
        tmp_path / "b.wav",
        silence,
        tmp_path / "c.wav",
    ]

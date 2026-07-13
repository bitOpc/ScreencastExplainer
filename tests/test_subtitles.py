from pathlib import Path

from lib.subtitles import write_subtitles


def test_write_subtitles_creates_srt_and_ass(tmp_path: Path):
    timings = [
        {"start": 0.0, "end": 2.5, "text": "你好世界"},
        {"start": 2.5, "end": 5.0, "text": "第二句字幕"},
    ]
    srt_path = tmp_path / "captions.srt"
    ass_path = tmp_path / "captions.ass"
    write_subtitles(timings, srt_path, ass_path)
    srt_text = srt_path.read_text(encoding="utf-8")
    ass_text = ass_path.read_text(encoding="utf-8")
    assert "你好世界" in srt_text
    assert "00:00:00,000 --> 00:00:02,500" in srt_text
    assert "[Script Info]" in ass_text
    assert "Dialogue:" in ass_text

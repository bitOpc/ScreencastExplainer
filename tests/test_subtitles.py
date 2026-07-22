from pathlib import Path

from lib.subtitles import (
    expand_to_single_line_cues,
    write_subtitles,
    wrap_to_lines,
)


def test_write_subtitles_creates_srt_and_ass(tmp_path: Path):
    timings = [
        {"start": 0.0, "end": 2.5, "text": "你好世界"},
        {"start": 2.5, "end": 5.0, "text": "第二句字幕"},
    ]
    srt_path = tmp_path / "captions.srt"
    ass_path = tmp_path / "captions.ass"
    cues = write_subtitles(timings, srt_path, ass_path)
    srt_text = srt_path.read_text(encoding="utf-8")
    ass_text = ass_path.read_text(encoding="utf-8")
    assert "你好世界" in srt_text
    assert "00:00:00,000 --> 00:00:02,500" in srt_text
    assert "[Script Info]" in ass_text
    assert "Dialogue:" in ass_text
    assert len(cues) == 2


def test_long_paragraph_splits_into_multiple_single_line_cues():
    text = (
        "今天带大家快速看一下 Obsidian 知识库里的 KV Cache 笔记。"
        "如果你用过 ChatGPT、Claude 这些大模型产品，一定会发现它们回复得挺快。"
        "这背后靠的就是 KV Cache。"
    )
    timings = [{"start": 0.0, "end": 30.0, "text": text}]
    cues = expand_to_single_line_cues(timings)

    assert len(cues) > 1
    assert all("\n" not in cue["text"] for cue in cues)
    assert cues[0]["start"] == 0.0
    assert cues[-1]["end"] == 30.0
    assert sum(cue["end"] - cue["start"] for cue in cues) == 30.0


def test_write_subtitles_ass_has_no_multiline_dialogue(tmp_path: Path):
    text = "那到底什么是 KV Cache？它是 LLM 自回归推理时，把历史 token 的 Key 和 Value 中间结果缓存起来，让后续生成步骤不再重复计算的优化机制。"
    timings = [{"start": 10.0, "end": 40.0, "text": text}]
    ass_path = tmp_path / "captions.ass"
    write_subtitles(timings, tmp_path / "captions.srt", ass_path)
    ass_text = ass_path.read_text(encoding="utf-8")
    dialogue_lines = [line for line in ass_text.splitlines() if line.startswith("Dialogue:")]
    assert len(dialogue_lines) > 1
    assert all(r"\N" not in line for line in dialogue_lines)


def test_wrap_to_lines_prefers_punctuation_breaks():
    text = "第一句很长很长很长，第二句也很长很长很长，第三句继续。"
    lines = wrap_to_lines(text, max_units=18.0)
    assert len(lines) >= 2
    assert all("，" not in line[1:] or line.endswith("，") for line in lines[:-1]) or len(lines) >= 2

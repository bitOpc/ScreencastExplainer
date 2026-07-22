"""生成 SRT 与 ASS 硬字幕文件。"""

import re
from pathlib import Path

from lib.timefmt import ass_time, srt_time

DEFAULT_MAX_LINE_UNITS = 38.0
PREFERRED_BREAKS = "，。！？；、："


def visual_width(char: str) -> float:
    if ord(char) > 127:
        return 2.0
    if char.isspace():
        return 0.5
    if char in "il.,;:|!":
        return 0.45
    return 0.9


def line_visual_width(text: str) -> float:
    return sum(visual_width(char) for char in text)


def wrap_to_lines(text: str, max_units: float = DEFAULT_MAX_LINE_UNITS) -> list[str]:
    """将文本拆成单行列表，每行不超过 max_units 视觉宽度。"""
    normalized = re.sub(r"\s+", " ", text.strip())
    if not normalized:
        return []

    lines: list[str] = []
    current = ""
    width = 0.0

    def flush() -> None:
        nonlocal current, width
        if current.strip():
            lines.append(current.strip())
        current = ""
        width = 0.0

    def append_char(char: str) -> None:
        nonlocal current, width
        char_width = visual_width(char)
        if current and width + char_width > max_units:
            break_at = -1
            for index, candidate in enumerate(current):
                if candidate in PREFERRED_BREAKS:
                    break_at = index
            if break_at >= 0 and break_at < len(current) - 1:
                head = current[: break_at + 1].strip()
                tail = current[break_at + 1 :].strip() + char
                if head:
                    lines.append(head)
                current = tail
                width = line_visual_width(current)
                return
            flush()
        current += char
        width += char_width

    for char in normalized:
        append_char(char)
    flush()
    return lines


def expand_to_single_line_cues(
    timings: list[dict],
    *,
    max_line_units: float = DEFAULT_MAX_LINE_UNITS,
) -> list[dict]:
    """把旁白段落时序展开为多条单行字幕时序。"""
    cues: list[dict] = []
    for item in timings:
        start = float(item["start"])
        end = float(item["end"])
        duration = max(end - start, 0.001)
        lines = wrap_to_lines(item["text"], max_units=max_line_units)
        if not lines:
            continue
        if len(lines) == 1:
            cues.append({"start": start, "end": end, "text": lines[0]})
            continue

        weights = [max(line_visual_width(line), 1.0) for line in lines]
        total_weight = sum(weights)
        cursor = start
        for index, line in enumerate(lines):
            if index == len(lines) - 1:
                cue_end = end
            else:
                cue_end = start + duration * (sum(weights[: index + 1]) / total_weight)
            cues.append({"start": cursor, "end": cue_end, "text": line})
            cursor = cue_end
    return cues


def escape_ass_text(text: str) -> str:
    return text.replace("{", r"\{").replace("}", r"\}")


def write_subtitles(timings: list[dict], srt_path: Path, ass_path: Path) -> list[dict]:
    """写入 SRT/ASS；长段落会按单行拆成多条时序字幕。"""
    cues = expand_to_single_line_cues(timings)
    srt_blocks = []
    ass_rows = []
    for index, item in enumerate(cues, start=1):
        start = item["start"]
        end = item["end"]
        text = item["text"]
        srt_blocks.append(f"{index}\n{srt_time(start)} --> {srt_time(end)}\n{text}")
        ass_text = escape_ass_text(text)
        ass_rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{ass_text}")

    srt_path.write_text("\n\n".join(srt_blocks) + "\n", encoding="utf-8")
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,STHeiti,42,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,4,1,2,130,130,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_path.write_text(header + "\n".join(ass_rows) + "\n", encoding="utf-8")
    return cues

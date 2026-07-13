"""生成 SRT 与 ASS 硬字幕文件。"""

import re
from pathlib import Path

from lib.timefmt import ass_time, srt_time


def visual_width(char: str) -> float:
    if ord(char) > 127:
        return 2.0
    if char.isspace():
        return 0.5
    if char in "il.,;:|!":
        return 0.45
    return 0.9


def wrap_ass_text(text: str, max_units: float = 54.0) -> str:
    lines: list[str] = []
    line = ""
    width = 0.0
    for char in re.sub(r"\s+", " ", text.strip()):
        w = visual_width(char)
        if line and width + w > max_units:
            lines.append(line.strip())
            line = char
            width = w
        else:
            line += char
            width += w
    if line.strip():
        lines.append(line.strip())
    return r"\N".join(lines[:3])


def write_subtitles(timings: list[dict], srt_path: Path, ass_path: Path) -> None:
    srt_blocks = []
    ass_rows = []
    for index, item in enumerate(timings, start=1):
        start = item["start"]
        end = item["end"]
        text = item["text"]
        srt_blocks.append(f"{index}\n{srt_time(start)} --> {srt_time(end)}\n{text}")
        ass_text = wrap_ass_text(text).replace("{", r"\{").replace("}", r"\}")
        ass_rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Default,,0,0,0,,{ass_text}")

    srt_path.write_text("\n\n".join(srt_blocks) + "\n", encoding="utf-8")
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,STHeiti,42,&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,-1,0,0,0,100,100,0,0,1,4,1,2,130,130,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_path.write_text(header + "\n".join(ass_rows) + "\n", encoding="utf-8")

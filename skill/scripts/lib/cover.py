"""根据成片内容与运行元数据生成 YouTube 风格封面图。"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from lib.ffmpeg_util import ffmpeg_path, probe_duration
from lib.timefmt import parse_srt_time

COVER_WIDTH = 1280
COVER_HEIGHT = 720
OVERLAY_ALPHA = 0.48
TITLE_COLOR = (255, 210, 55)
SUBTITLE_COLOR = (255, 255, 255)
SUBTITLE_STROKE = (0, 0, 0)
TITLE_SHADOW = (0, 0, 0, 170)
SUBTITLE_SHADOW = (0, 0, 0, 210)

TITLE_FONT_PATH = "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf"
TITLE_FONT_FALLBACK = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
SUBTITLE_FONT_PATH = "/System/Library/Fonts/STHeiti Medium.ttc"
SUBTITLE_FONT_INDEX = 0
TITLE_MAX_WIDTH_RATIO = 0.72
SUBTITLE_MAX_WIDTH_RATIO = 0.94

_FONT_CANDIDATES = [
    SUBTITLE_FONT_PATH,
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

_ENGLISH_TOPIC_RE = re.compile(
    r"`([A-Za-z][A-Za-z0-9 _-]{1,40})`|"
    r"\b(Transformer|Attention|KV Cache|RAG|Agent|LLM|GPT|Claude|Gemini|Obsidian)\b"
)
_SECTION_RE = re.compile(r"^##\s+\d+\s*[—-]\s*(.+)$", re.MULTILINE)
_SWITCH_HINT_RE = re.compile(r"切换|切到|视角切")
_AFTER_SWITCH_TOPIC_RE = re.compile(
    r"切换到[^A-Za-z`]*`?([A-Za-z][A-Za-z0-9 _-]{1,30})`?|"
    r"切到[^A-Za-z`]*`?([A-Za-z][A-Za-z0-9 _-]{1,30})`?"
)
_TOPIC_SUBTITLE_HINTS = {
    "attention": "机制深度解析",
    "transformer": "架构深度解析",
    "kv cache": "原理深度解析",
}


def _topic_subtitle(title: str, page_target: str) -> str:
    key = title.casefold()
    if key in _TOPIC_SUBTITLE_HINTS:
        return _TOPIC_SUBTITLE_HINTS[key]
    return _subtitle_from_page_target(page_target)


@dataclass(frozen=True)
class CoverText:
    title: str
    subtitle: str
    frame_seconds: float
    source: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _unique_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _english_topics(*texts: str) -> list[str]:
    found: list[str] = []
    for text in texts:
        for match in _ENGLISH_TOPIC_RE.finditer(text):
            token = (match.group(1) or match.group(2)).strip()
            if token and token not in {"Obsidian"}:
                found.append(token)
    return _unique_preserve(found)


def _subtitle_from_page_target(page_target: str) -> str:
    cleaned = page_target.strip()
    cleaned = re.sub(r"笔记.*", "", cleaned).strip()
    cleaned = re.sub(r"[：:].*", "", cleaned).strip()
    if not cleaned:
        return "深度解析"
    if len(cleaned) <= 12:
        return cleaned
    return cleaned[:12]


def _subtitle_from_section(section_title: str) -> str:
    text = section_title.strip()
    text = re.sub(r"`[^`]+`", "", text).strip()
    text = re.sub(r"^(先看|继续|再往后|接着|然后|现在|最后)", "", text).strip()
    if len(text) > 14:
        text = text[:14]
    return text or "深度解析"


def _segment_start_seconds(segment: dict[str, Any]) -> float:
    start = segment.get("start")
    if isinstance(start, str):
        return parse_srt_time(start)
    if isinstance(start, (int, float)):
        return float(start)
    return 0.0


def _click_times(actions: dict[str, Any]) -> list[float]:
    return [
        float(event["at"])
        for event in actions.get("events", [])
        if event.get("action") == "click" and "at" in event
    ]


def infer_cover_text(
    *,
    run_data: dict[str, Any] | None,
    segments_data: dict[str, Any] | None,
    script_text: str | None,
    actions_data: dict[str, Any] | None,
    video_duration: float,
    title_override: str | None = None,
    subtitle_override: str | None = None,
    frame_seconds_override: float | None = None,
) -> CoverText:
    """从运行产物推断封面标题、副标题与取帧时间。"""
    if title_override and subtitle_override and frame_seconds_override is not None:
        return CoverText(
            title=title_override,
            subtitle=subtitle_override,
            frame_seconds=frame_seconds_override,
            source="cli",
        )

    segments = (segments_data or {}).get("segments", [])
    target_description = (run_data or {}).get("target_description", "")
    script_text = script_text or ""

    section_titles = [_subtitle_from_section(m.group(1)) for m in _SECTION_RE.finditer(script_text)]
    topics = _english_topics(target_description, script_text, *(s.get("page_target", "") for s in segments))

    chosen_segment = segments[-1] if segments else None
    switch_index: int | None = None
    click_times = _click_times(actions_data or {})
    for index, segment in enumerate(segments):
        notes = str(segment.get("notes", ""))
        text = str(segment.get("text", ""))
        page_target = str(segment.get("page_target", ""))
        if _SWITCH_HINT_RE.search(notes) or _SWITCH_HINT_RE.search(text) or _SWITCH_HINT_RE.search(page_target):
            switch_index = index
            chosen_segment = segment
            break

    if switch_index is not None and switch_index + 1 < len(segments):
        chosen_segment = segments[switch_index + 1]

    title = title_override or (topics[-1] if topics else "Screencast")
    if chosen_segment and not title_override:
        page_target = str(chosen_segment.get("page_target", ""))
        page_topics = _english_topics(page_target)
        if page_topics:
            title = page_topics[0]
        elif switch_index is not None:
            prior = segments[switch_index]
            for source in (
                str(prior.get("page_target", "")),
                str(prior.get("text", "")),
                str(prior.get("notes", "")),
            ):
                match = _AFTER_SWITCH_TOPIC_RE.search(source)
                if match:
                    title = (match.group(1) or match.group(2)).strip()
                    break

    subtitle = subtitle_override
    if not subtitle and chosen_segment:
        subtitle = _topic_subtitle(title, str(chosen_segment.get("page_target", "")))
    if not subtitle and section_titles:
        subtitle = section_titles[min(len(section_titles) - 1, max(0, len(section_titles) // 2))]
    if not subtitle:
        subtitle = _subtitle_from_page_target(target_description) if target_description else "深度解析"

    frame_seconds = frame_seconds_override
    if frame_seconds is None and click_times and switch_index is not None:
        frame_seconds = click_times[min(switch_index, len(click_times) - 1)] + 2.0
    if frame_seconds is None and chosen_segment:
        frame_seconds = _segment_start_seconds(chosen_segment) + 2.0
    if frame_seconds is None:
        frame_seconds = max(1.0, video_duration * 0.4)
    frame_seconds = min(max(0.5, frame_seconds), max(0.5, video_duration - 0.5))

    return CoverText(
        title=title,
        subtitle=subtitle,
        frame_seconds=frame_seconds,
        source="inferred",
    )


def _resolve_font(size: int, *, path: str | None = None, index: int = 0) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [path] if path else _FONT_CANDIDATES
    for font_path in candidates:
        if font_path and Path(font_path).exists():
            try:
                return ImageFont.truetype(font_path, size=size, index=index)
            except OSError:
                try:
                    return ImageFont.truetype(font_path, size=size)
                except OSError:
                    continue
    return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    path: str,
    max_width: int,
    start_size: int,
    min_size: int,
    index: int = 0,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for size in range(start_size, min_size - 1, -2):
        font = _resolve_font(size, path=path, index=index)
        bbox = draw.textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
    return _resolve_font(min_size, path=path, index=index)


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_title(draw: ImageDraw.ImageDraw, center_x: float, y: float, text: str, font: ImageFont.ImageFont) -> int:
    width, height = _text_size(draw, text, font)
    x = center_x - width / 2
    for offset in ((5, 5), (3, 3)):
        draw.text(
            (x + offset[0], y + offset[1]),
            text,
            font=font,
            fill=TITLE_SHADOW,
        )
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(*TITLE_COLOR, 255),
        stroke_width=2,
        stroke_fill=(0, 0, 0, 220),
    )
    return height


def _draw_subtitle(draw: ImageDraw.ImageDraw, center_x: float, y: float, text: str, font: ImageFont.ImageFont) -> int:
    width, height = _text_size(draw, text, font)
    x = center_x - width / 2
    for offset in ((6, 8), (4, 6), (2, 4)):
        draw.text(
            (x + offset[0], y + offset[1]),
            text,
            font=font,
            fill=SUBTITLE_SHADOW,
            stroke_width=10,
            stroke_fill=(0, 0, 0, 255),
        )
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(*SUBTITLE_COLOR, 255),
        stroke_width=8,
        stroke_fill=(*SUBTITLE_STROKE, 255),
    )
    return height


def extract_video_frame(*, video_path: Path, timestamp: float, output_path: Path) -> None:
    """从视频指定时间点截取一帧 PNG。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            ffmpeg_path(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            str(output_path),
        ],
        check=True,
    )


def _fit_cover_frame(image: Image.Image) -> Image.Image:
    """居中裁剪并缩放到封面尺寸。"""
    target_ratio = COVER_WIDTH / COVER_HEIGHT
    width, height = image.size
    current_ratio = width / height
    if current_ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        image = image.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        image = image.crop((0, top, width, top + new_height))
    return image.resize((COVER_WIDTH, COVER_HEIGHT), Image.Resampling.LANCZOS)


def render_cover_image(
    *,
    frame_path: Path,
    title: str,
    subtitle: str,
    output_path: Path,
) -> Path:
    """将视频帧渲染为带暗色遮罩与标题文字的封面图。"""
    base = _fit_cover_frame(Image.open(frame_path).convert("RGB"))
    overlay = Image.new("RGBA", base.size, (0, 0, 0, int(255 * OVERLAY_ALPHA)))
    composed = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(composed)

    center_x = COVER_WIDTH / 2
    title_font_path = (
        TITLE_FONT_PATH
        if Path(TITLE_FONT_PATH).exists()
        else TITLE_FONT_FALLBACK
        if Path(TITLE_FONT_FALLBACK).exists()
        else _FONT_CANDIDATES[0]
    )
    title_font = _fit_font(
        draw,
        title,
        path=title_font_path,
        max_width=int(COVER_WIDTH * TITLE_MAX_WIDTH_RATIO),
        start_size=92,
        min_size=60,
    )
    subtitle_font = _fit_font(
        draw,
        subtitle,
        path=SUBTITLE_FONT_PATH if Path(SUBTITLE_FONT_PATH).exists() else _FONT_CANDIDATES[0],
        max_width=int(COVER_WIDTH * SUBTITLE_MAX_WIDTH_RATIO),
        start_size=122,
        min_size=72,
        index=SUBTITLE_FONT_INDEX,
    )

    gap = 28
    _, subtitle_h = _text_size(draw, subtitle, subtitle_font)
    _, title_h = _text_size(draw, title, title_font)
    block_h = title_h + gap + subtitle_h
    y = (COVER_HEIGHT - block_h) / 2 - 12

    title_h = _draw_title(draw, center_x, y, title, title_font)
    _draw_subtitle(draw, center_x, y + title_h + gap, subtitle, subtitle_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path


def build_cover(
    *,
    video_path: Path,
    output_path: Path,
    run_data: dict[str, Any] | None = None,
    segments_data: dict[str, Any] | None = None,
    script_text: str | None = None,
    actions_data: dict[str, Any] | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    frame_seconds: float | None = None,
) -> tuple[Path, CoverText]:
    """生成封面图并返回输出路径与推断元数据。"""
    if not video_path.is_file():
        raise FileNotFoundError(f"未找到视频文件: {video_path}")

    duration = probe_duration(video_path)
    cover_text = infer_cover_text(
        run_data=run_data,
        segments_data=segments_data,
        script_text=script_text,
        actions_data=actions_data,
        video_duration=duration,
        title_override=title,
        subtitle_override=subtitle,
        frame_seconds_override=frame_seconds,
    )

    with tempfile.TemporaryDirectory(prefix="screencast-cover-") as tmp:
        frame_path = Path(tmp) / "frame.png"
        extract_video_frame(
            video_path=video_path,
            timestamp=cover_text.frame_seconds,
            output_path=frame_path,
        )
        render_cover_image(
            frame_path=frame_path,
            title=cover_text.title,
            subtitle=cover_text.subtitle,
            output_path=output_path,
        )
    return output_path, cover_text


def load_run_context(paths_root: Path) -> dict[str, Any]:
    """读取运行目录中的封面推断上下文。"""
    context: dict[str, Any] = {}
    run_json = paths_root / "run.json"
    segments_json = paths_root / "segments.json"
    script_md = paths_root / "script.md"
    actions_json = paths_root / "actions.json"

    if run_json.is_file():
        context["run_data"] = _load_json(run_json)
    if segments_json.is_file():
        context["segments_data"] = _load_json(segments_json)
    if script_md.is_file():
        context["script_text"] = script_md.read_text(encoding="utf-8")
    if actions_json.is_file():
        context["actions_data"] = _load_json(actions_json)
    return context

"""根据 Agent 提供的文案与成片帧生成 YouTube 风格封面图。

标题 / 副标题钩子由跑 Skill 的 LLM Agent 写入 ``cover.json``（或 CLI 覆盖）；
本模块只负责：解析契约、推断取帧时间、渲染。不内置话题钩子硬编码。
"""

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

# 默认字体仅为渲染回退；可通过 cover.json / CLI 覆盖。
DEFAULT_TITLE_FONT = "/System/Library/Fonts/Supplemental/Times New Roman Bold Italic.ttf"
DEFAULT_TITLE_FONT_FALLBACK = "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf"
DEFAULT_SUBTITLE_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
DEFAULT_SUBTITLE_FONT_INDEX = 0
TITLE_MAX_WIDTH_RATIO = 0.72
SUBTITLE_MAX_WIDTH_RATIO = 0.94

_FONT_CANDIDATES = [
    DEFAULT_SUBTITLE_FONT,
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
]

_SWITCH_HINT_RE = re.compile(r"切换|切到|视角切")


@dataclass(frozen=True)
class CoverText:
    title: str
    subtitle: str
    frame_seconds: float
    source: str
    title_font: str | None = None
    subtitle_font: str | None = None
    subtitle_font_index: int = DEFAULT_SUBTITLE_FONT_INDEX


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def infer_frame_seconds(
    *,
    segments_data: dict[str, Any] | None,
    actions_data: dict[str, Any] | None,
    video_duration: float,
) -> float:
    """机械推断取帧时间：多主题切换点优先，否则开场。不决定文案。"""
    segments = (segments_data or {}).get("segments", [])
    click_times = _click_times(actions_data or {})

    switch_index: int | None = None
    for index, segment in enumerate(segments):
        blob = " ".join(
            str(segment.get(key, "")) for key in ("notes", "text", "page_target")
        )
        if _SWITCH_HINT_RE.search(blob):
            switch_index = index
            break

    if click_times and switch_index is not None:
        frame_seconds = click_times[min(switch_index, len(click_times) - 1)] + 2.0
    elif segments:
        opening = _segment_start_seconds(segments[0])
        frame_seconds = opening + min(8.0, max(3.0, video_duration * 0.05))
    else:
        frame_seconds = max(1.0, min(video_duration * 0.08, 12.0))

    return min(max(0.5, frame_seconds), max(0.5, video_duration - 0.5))


def resolve_cover_text(
    *,
    cover_data: dict[str, Any] | None,
    segments_data: dict[str, Any] | None,
    actions_data: dict[str, Any] | None,
    video_duration: float,
    title_override: str | None = None,
    subtitle_override: str | None = None,
    frame_seconds_override: float | None = None,
) -> CoverText:
    """合并 CLI / Agent ``cover.json`` 与机械取帧。

    标题与副标题必须由 Agent（cover.json）或 CLI 提供；脚本不编造钩子话术。
    """
    agent = cover_data or {}
    title = (title_override or str(agent.get("title") or "")).strip()
    subtitle = (subtitle_override or str(agent.get("subtitle") or "")).strip()

    if not title or not subtitle:
        raise ValueError(
            "缺少封面标题或副标题。请先由 Agent 根据 script.md / segments.json "
            "写入 cover.json（字段 title、subtitle），或通过 "
            "--title / --subtitle 传入。参见 skill/references/cover.md。"
        )

    if title_override and subtitle_override and frame_seconds_override is not None:
        source = "cli"
    elif title_override or subtitle_override or frame_seconds_override is not None:
        source = "cli+agent" if agent.get("title") or agent.get("subtitle") else "cli"
    else:
        source = "agent"

    frame_seconds = frame_seconds_override
    if frame_seconds is None and agent.get("frame_seconds") is not None:
        frame_seconds = float(agent["frame_seconds"])
    if frame_seconds is None:
        frame_seconds = infer_frame_seconds(
            segments_data=segments_data,
            actions_data=actions_data,
            video_duration=video_duration,
        )
    frame_seconds = min(max(0.5, float(frame_seconds)), max(0.5, video_duration - 0.5))

    title_font = agent.get("title_font")
    subtitle_font = agent.get("subtitle_font")
    subtitle_font_index = int(
        agent.get("subtitle_font_index", DEFAULT_SUBTITLE_FONT_INDEX)
    )

    return CoverText(
        title=title,
        subtitle=subtitle,
        frame_seconds=frame_seconds,
        source=source,
        title_font=str(title_font) if title_font else None,
        subtitle_font=str(subtitle_font) if subtitle_font else None,
        subtitle_font_index=subtitle_font_index,
    )


# 兼容旧测试名
def infer_cover_text(**kwargs: Any) -> CoverText:
    """已弃用：请改用 resolve_cover_text。保留包装以兼容旧调用。"""
    return resolve_cover_text(
        cover_data=kwargs.get("cover_data"),
        segments_data=kwargs.get("segments_data"),
        actions_data=kwargs.get("actions_data"),
        video_duration=kwargs["video_duration"],
        title_override=kwargs.get("title_override"),
        subtitle_override=kwargs.get("subtitle_override"),
        frame_seconds_override=kwargs.get("frame_seconds_override"),
    )


def _resolve_font(
    size: int, *, path: str | None = None, index: int = 0
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: list[str | None]
    if path:
        candidates = [path, *_FONT_CANDIDATES]
    else:
        candidates = list(_FONT_CANDIDATES)
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
    path: str | None,
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


def _text_size(
    draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _draw_title(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.ImageFont,
) -> int:
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


def _draw_subtitle(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    text: str,
    font: ImageFont.ImageFont,
) -> int:
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


def _default_title_font_path() -> str:
    if Path(DEFAULT_TITLE_FONT).exists():
        return DEFAULT_TITLE_FONT
    if Path(DEFAULT_TITLE_FONT_FALLBACK).exists():
        return DEFAULT_TITLE_FONT_FALLBACK
    return _FONT_CANDIDATES[0]


def render_cover_image(
    *,
    frame_path: Path,
    title: str,
    subtitle: str,
    output_path: Path,
    title_font: str | None = None,
    subtitle_font: str | None = None,
    subtitle_font_index: int = DEFAULT_SUBTITLE_FONT_INDEX,
) -> Path:
    """将视频帧渲染为带暗色遮罩与标题文字的封面图。"""
    base = _fit_cover_frame(Image.open(frame_path).convert("RGB"))
    overlay = Image.new("RGBA", base.size, (0, 0, 0, int(255 * OVERLAY_ALPHA)))
    composed = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(composed)

    center_x = COVER_WIDTH / 2
    title_font_path = title_font or _default_title_font_path()
    subtitle_font_path = subtitle_font or (
        DEFAULT_SUBTITLE_FONT
        if Path(DEFAULT_SUBTITLE_FONT).exists()
        else _FONT_CANDIDATES[0]
    )

    fitted_title = _fit_font(
        draw,
        title,
        path=title_font_path,
        max_width=int(COVER_WIDTH * TITLE_MAX_WIDTH_RATIO),
        start_size=92,
        min_size=60,
    )
    fitted_subtitle = _fit_font(
        draw,
        subtitle,
        path=subtitle_font_path,
        max_width=int(COVER_WIDTH * SUBTITLE_MAX_WIDTH_RATIO),
        start_size=122,
        min_size=72,
        index=subtitle_font_index,
    )

    gap = 28
    _, title_h = _text_size(draw, title, fitted_title)
    _, subtitle_h = _text_size(draw, subtitle, fitted_subtitle)
    block_h = title_h + gap + subtitle_h
    y = (COVER_HEIGHT - block_h) / 2 - 12

    title_h = _draw_title(draw, center_x, y, title, fitted_title)
    _draw_subtitle(draw, center_x, y + title_h + gap, subtitle, fitted_subtitle)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    composed.convert("RGB").save(output_path, format="PNG", optimize=True)
    return output_path


def build_cover(
    *,
    video_path: Path,
    output_path: Path,
    cover_data: dict[str, Any] | None = None,
    run_data: dict[str, Any] | None = None,
    segments_data: dict[str, Any] | None = None,
    script_text: str | None = None,
    actions_data: dict[str, Any] | None = None,
    title: str | None = None,
    subtitle: str | None = None,
    frame_seconds: float | None = None,
) -> tuple[Path, CoverText]:
    """生成封面图并返回输出路径与文案元数据。"""
    del run_data, script_text  # 文案由 Agent cover.json / CLI 提供，不再脚本推断
    if not video_path.is_file():
        raise FileNotFoundError(f"未找到视频文件: {video_path}")

    duration = probe_duration(video_path)
    cover_text = resolve_cover_text(
        cover_data=cover_data,
        segments_data=segments_data,
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
            title_font=cover_text.title_font,
            subtitle_font=cover_text.subtitle_font,
            subtitle_font_index=cover_text.subtitle_font_index,
        )
    return output_path, cover_text


def load_run_context(paths_root: Path) -> dict[str, Any]:
    """读取运行目录中的封面渲染上下文。"""
    context: dict[str, Any] = {}
    run_json = paths_root / "run.json"
    segments_json = paths_root / "segments.json"
    script_md = paths_root / "script.md"
    actions_json = paths_root / "actions.json"
    cover_json = paths_root / "cover.json"

    if run_json.is_file():
        context["run_data"] = _load_json(run_json)
    if segments_json.is_file():
        context["segments_data"] = _load_json(segments_json)
    if script_md.is_file():
        context["script_text"] = script_md.read_text(encoding="utf-8")
    if actions_json.is_file():
        context["actions_data"] = _load_json(actions_json)
    if cover_json.is_file():
        context["cover_data"] = _load_json(cover_json)
    return context

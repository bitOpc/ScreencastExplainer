"""封面生成单元测试。"""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from lib.cover import (
    CoverText,
    infer_frame_seconds,
    render_cover_image,
    resolve_cover_text,
)
from lib.paths import RunPaths


def test_resolve_cover_text_requires_agent_or_cli_copy():
    with pytest.raises(ValueError, match="cover.json"):
        resolve_cover_text(
            cover_data=None,
            segments_data=None,
            actions_data=None,
            video_duration=120.0,
        )


def test_resolve_cover_text_from_agent_cover_json():
    cover = resolve_cover_text(
        cover_data={
            "title": "Prompt Engineering",
            "subtitle": "Prompt 是越长越好吗？",
            "frame_seconds": 8,
        },
        segments_data=None,
        actions_data=None,
        video_duration=155.0,
    )
    assert cover == CoverText(
        title="Prompt Engineering",
        subtitle="Prompt 是越长越好吗？",
        frame_seconds=8.0,
        source="agent",
    )


def test_resolve_cover_text_cli_override():
    cover = resolve_cover_text(
        cover_data={"title": "Ignored", "subtitle": "Ignored"},
        segments_data=None,
        actions_data=None,
        video_duration=120.0,
        title_override="KV Cache",
        subtitle_override="机制深度解析",
        frame_seconds_override=42.0,
    )
    assert cover.title == "KV Cache"
    assert cover.subtitle == "机制深度解析"
    assert cover.frame_seconds == 42.0
    assert cover.source == "cli"


def test_infer_frame_seconds_prefers_switch_click():
    frame = infer_frame_seconds(
        segments_data={
            "segments": [
                {"id": 1, "start": "00:00:00,000", "notes": "开场"},
                {
                    "id": 7,
                    "start": "00:05:18,088",
                    "notes": "切换到 Attention 这篇",
                    "text": "现在把视角切到 Attention",
                },
            ]
        },
        actions_data={"events": [{"at": 318.0, "action": "click"}]},
        video_duration=600.0,
    )
    assert frame == pytest.approx(320.0, abs=0.01)


def test_infer_frame_seconds_defaults_to_opening():
    frame = infer_frame_seconds(
        segments_data={
            "segments": [
                {"id": 1, "start": "00:00:00,000", "notes": "开场"},
                {"id": 10, "start": "00:02:17,154", "notes": "小结"},
            ]
        },
        actions_data={"events": [{"at": 16.0, "action": "key", "key": "PageDown"}]},
        video_duration=155.0,
    )
    assert frame == pytest.approx(7.75, abs=0.5)
    assert frame < 30


def test_render_cover_image_writes_png(tmp_path: Path):
    frame_path = tmp_path / "frame.png"
    Image.new("RGB", (1920, 1080), color=(30, 30, 30)).save(frame_path)
    output_path = tmp_path / "cover.png"

    render_cover_image(
        frame_path=frame_path,
        title="Attention",
        subtitle="机制深度解析",
        output_path=output_path,
    )

    assert output_path.is_file()
    with Image.open(output_path) as image:
        assert image.size == (1280, 720)


def test_build_cover_end_to_end(tmp_run_dir, tmp_path: Path):
    from build_cover import _pick_video_path
    from lib.cover import build_cover

    paths = RunPaths(tmp_run_dir)
    paths.video_dir.mkdir(parents=True, exist_ok=True)
    video_path = paths.video_dir / "final.mp4"
    video_path.write_bytes(b"fake")

    paths.cover_json.write_text(
        '{"title":"Attention","subtitle":"机制深度解析","frame_seconds":12}',
        encoding="utf-8",
    )

    fake_frame = tmp_path / "frame.png"
    Image.new("RGB", (1440, 900), color=(10, 10, 10)).save(fake_frame)

    with patch("lib.cover.probe_duration", return_value=600.0):
        with patch("lib.cover.extract_video_frame") as extract:

            def _write_frame(**kwargs):
                kwargs["output_path"].write_bytes(fake_frame.read_bytes())

            extract.side_effect = lambda **kwargs: _write_frame(**kwargs)
            output, cover_text = build_cover(
                video_path=video_path,
                output_path=paths.cover_png,
                cover_data={
                    "title": "Attention",
                    "subtitle": "机制深度解析",
                    "frame_seconds": 12,
                },
            )

    assert output == paths.cover_png
    assert cover_text.title == "Attention"
    assert cover_text.subtitle == "机制深度解析"
    assert paths.cover_png.is_file()
    assert _pick_video_path(paths, None) == video_path

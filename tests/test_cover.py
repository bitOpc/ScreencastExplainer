"""封面生成单元测试。"""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from lib.cover import (
    CoverText,
    infer_cover_text,
    render_cover_image,
    _subtitle_from_page_target,
)
from lib.paths import RunPaths


def test_subtitle_from_page_target_strips_note_suffix():
    assert _subtitle_from_page_target("Attention 笔记顶部标题区") == "Attention"


def test_infer_cover_text_prefers_switch_segment():
    segments_data = {
        "segments": [
            {
                "id": 1,
                "start": "00:00:00,000",
                "page_target": "Transformer 笔记顶部",
                "notes": "开场",
            },
            {
                "id": 7,
                "start": "00:05:18,088",
                "page_target": "Attention 笔记顶部标题区",
                "notes": "切换到 Attention 这篇",
                "text": "现在把视角切到 Attention 这篇",
            },
        ]
    }
    actions_data = {
        "events": [
            {"at": 318.0, "action": "click"},
        ]
    }

    cover = infer_cover_text(
        run_data={"target_description": "Transformer 与 Attention 讲解"},
        segments_data=segments_data,
        script_text="# Demo\n## 01 — Transformer 定位\n",
        actions_data=actions_data,
        video_duration=600.0,
    )

    assert cover.title == "Attention"
    assert cover.subtitle == "机制深度解析"
    assert cover.frame_seconds == pytest.approx(320.0, abs=0.01)


def test_infer_cover_text_cli_override():
    cover = infer_cover_text(
        run_data=None,
        segments_data=None,
        script_text=None,
        actions_data=None,
        video_duration=120.0,
        title_override="KV Cache",
        subtitle_override="机制深度解析",
        frame_seconds_override=42.0,
    )
    assert cover == CoverText(
        title="KV Cache",
        subtitle="机制深度解析",
        frame_seconds=42.0,
        source="cli",
    )


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

    paths.script_md.write_text(
        "# Demo\n## 07 — 切换到 Attention\n",
        encoding="utf-8",
    )
    paths.segments_json.write_text(
        """{
  "segments": [
    {"id": 1, "start": "00:00:00,000", "page_target": "Transformer 顶部"},
    {"id": 2, "start": "00:05:00,000", "page_target": "Attention 机制讲解", "notes": "切换到 Attention"}
  ]
}""",
        encoding="utf-8",
    )
    paths.run_json.write_text(
        '{"target_description":"Attention 机制讲解"}',
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
                segments_data={
                    "segments": [
                        {
                            "id": 2,
                            "start": "00:05:00,000",
                            "page_target": "Attention 机制讲解",
                            "notes": "切换到 Attention",
                        }
                    ]
                },
                script_text=paths.script_md.read_text(encoding="utf-8"),
            )

    assert output == paths.cover_png
    assert cover_text.title == "Attention"
    assert paths.cover_png.is_file()
    assert _pick_video_path(paths, None) == video_path

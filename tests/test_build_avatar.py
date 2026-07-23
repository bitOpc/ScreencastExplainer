"""build_avatar.py 单元测试。"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from build_avatar import build_avatar, list_narration_clips
from lib.paths import RunPaths


def test_list_narration_clips_sorted(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    clips = paths.work_audio_dir / "edge_clips"
    clips.mkdir(parents=True)
    (clips / "clip_002.wav").write_bytes(b"x")
    (clips / "clip_001.wav").write_bytes(b"x")

    found = list_narration_clips(paths)

    assert [path.name for path in found] == ["clip_001.wav", "clip_002.wav"]


def test_build_avatar_requires_confirmation(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.avatar_json.write_text(
        json.dumps({"use_presenter": False, "source_image": "a.png"}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="use_presenter"):
        build_avatar(paths)


def test_build_avatar_calls_sadtalker_per_clip(tmp_run_dir, tmp_path):
    paths = RunPaths(tmp_run_dir)
    paths.ensure_dirs()
    photo = tmp_path / "face.png"
    photo.write_bytes(b"img")
    paths.avatar_json.write_text(
        json.dumps(
            {
                "use_presenter": True,
                "source_image": str(photo),
                "estimated_seconds": 2,
                "user_confirmed_slow": True,
            }
        ),
        encoding="utf-8",
    )
    clips = paths.work_audio_dir / "edge_clips"
    clips.mkdir(parents=True)
    (clips / "clip_001.wav").write_bytes(b"x")
    (clips / "clip_002.wav").write_bytes(b"x")
    cfg = {
        "sadtalker_root": str(tmp_path / "sadtalker"),
        "sadtalker": {
            "still": True,
            "preprocess": "full",
            "face_model_resolution": 512,
        },
        "has_cuda": False,
    }

    with patch("build_avatar.run_sadtalker_segment") as mock_segment, patch(
        "build_avatar.concat_avatar_clips"
    ) as mock_concat:

        def fake_segment(**kwargs):
            kwargs["out_mp4"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["out_mp4"].write_bytes(b"mp4")

        mock_segment.side_effect = fake_segment
        mock_concat.side_effect = (
            lambda clip_mp4s, gap_seconds, output: output.write_bytes(b"out")
        )
        output = build_avatar(paths, presenter_cfg=cfg)

    assert mock_segment.call_count == 2
    assert output == paths.avatar_mp4
    report = json.loads(paths.avatar_report_json.read_text(encoding="utf-8"))
    assert len(report["segments"]) == 2
    assert all(segment["status"] == "ok" for segment in report["segments"])


def test_build_avatar_missing_source_image(tmp_run_dir, tmp_path):
    paths = RunPaths(tmp_run_dir)
    paths.ensure_dirs()
    missing_photo = tmp_path / "missing.png"
    paths.avatar_json.write_text(
        json.dumps(
            {
                "use_presenter": True,
                "source_image": str(missing_photo),
                "estimated_seconds": 2,
                "user_confirmed_slow": True,
            }
        ),
        encoding="utf-8",
    )
    clips = paths.work_audio_dir / "edge_clips"
    clips.mkdir(parents=True)
    (clips / "clip_001.wav").write_bytes(b"x")

    with pytest.raises(ValueError, match="头像源图片不存在"):
        build_avatar(paths)


def test_build_avatar_segment_failure_stops_early(tmp_run_dir, tmp_path):
    paths = RunPaths(tmp_run_dir)
    paths.ensure_dirs()
    photo = tmp_path / "face.png"
    photo.write_bytes(b"img")
    paths.avatar_json.write_text(
        json.dumps(
            {
                "use_presenter": True,
                "source_image": str(photo),
                "estimated_seconds": 2,
                "user_confirmed_slow": True,
            }
        ),
        encoding="utf-8",
    )
    clips = paths.work_audio_dir / "edge_clips"
    clips.mkdir(parents=True)
    (clips / "clip_001.wav").write_bytes(b"x")
    (clips / "clip_002.wav").write_bytes(b"x")
    (clips / "clip_003.wav").write_bytes(b"x")
    cfg = {
        "sadtalker_root": str(tmp_path / "sadtalker"),
        "sadtalker": {
            "still": True,
            "preprocess": "full",
            "face_model_resolution": 512,
        },
        "has_cuda": False,
    }

    with patch("build_avatar.run_sadtalker_segment") as mock_segment, patch(
        "build_avatar.concat_avatar_clips"
    ) as mock_concat:

        def fake_segment(**kwargs):
            if kwargs["out_mp4"].name == "clip_002.mp4":
                raise RuntimeError("SadTalker failed on segment 2")
            kwargs["out_mp4"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["out_mp4"].write_bytes(b"mp4")

        mock_segment.side_effect = fake_segment

        with pytest.raises(RuntimeError, match="SadTalker 生成第 2 段失败"):
            build_avatar(paths, presenter_cfg=cfg)

    assert mock_segment.call_count == 2
    mock_concat.assert_not_called()
    report = json.loads(paths.avatar_report_json.read_text(encoding="utf-8"))
    assert len(report["segments"]) == 2
    assert report["segments"][0]["status"] == "ok"
    assert report["segments"][1]["status"] == "failed"

from pathlib import Path

from lib.presenter_config import (
    default_presenter_config,
    estimate_avatar_minutes,
    install_avatar_image,
    load_presenter_config,
    save_presenter_config,
)


def test_default_config_keys():
    cfg = default_presenter_config()
    assert cfg["enabled"] is False
    assert cfg["installed"] is False
    assert cfg["avatar_image"] is None
    assert cfg["layout"]["shape"] == "circle"


def test_save_and_load_roundtrip(tmp_path):
    path = tmp_path / "presenter.json"
    data = default_presenter_config()
    data["enabled"] = True
    save_presenter_config(data, path)
    loaded = load_presenter_config(path)
    assert loaded["enabled"] is True


def test_estimate_cuda_range():
    result = estimate_avatar_minutes(600.0, has_cuda=True)
    assert result["needs_slow_confirm"] is False
    assert result["min_minutes"] == 20.0  # 600*2/60
    assert result["max_minutes"] == 40.0  # 600*4/60


def test_estimate_cpu_needs_slow_confirm():
    result = estimate_avatar_minutes(600.0, has_cuda=False)
    assert result["needs_slow_confirm"] is True
    assert "数小时" in result["label"]


def test_install_avatar_image_copies(tmp_path):
    src = tmp_path / "photo.jpg"
    src.write_bytes(b"fake")
    dest_dir = tmp_path / "avatars"
    dest = dest_dir / "default.png"
    out = install_avatar_image(src, dest)
    assert out == dest
    assert dest.is_file()

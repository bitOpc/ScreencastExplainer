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
    assert result["min_minutes"] == 15.0  # 600*1.5/60
    assert result["max_minutes"] == 30.0  # 600*3/60


def test_default_sadtalker_is_fast_profile():
    cfg = default_presenter_config()
    assert cfg["profile"] == "fast"
    assert cfg["sadtalker"]["face_model_resolution"] == 256
    assert cfg["sadtalker"]["preprocess"] == "crop"
    assert cfg["sadtalker"]["batch_size"] == 4


def test_resolve_sadtalker_clamps_batch_without_cuda():
    from lib.presenter_config import resolve_sadtalker_settings

    settings = resolve_sadtalker_settings(
        {"profile": "fast", "has_cuda": False, "sadtalker": {"batch_size": 8}}
    )
    assert settings["batch_size"] == 2


def test_resolve_sadtalker_quality_profile():
    from lib.presenter_config import resolve_sadtalker_settings

    settings = resolve_sadtalker_settings(
        {"profile": "quality", "has_cuda": True, "sadtalker": {}}
    )
    assert settings["face_model_resolution"] == 512
    assert settings["preprocess"] == "full"
    assert settings["batch_size"] == 2


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

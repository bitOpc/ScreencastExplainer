from doctor import check_dependencies


def test_check_dependencies_returns_dict():
    result = check_dependencies()
    assert "python3" in result
    assert "ffmpeg" in result
    assert "screencapture" in result
    assert "selected_voice" in result
    assert result["python3"] in {"available", "unavailable"}
    assert result["screencapture"] in {"available", "unavailable"}


def test_doctor_includes_optional_presenter_keys(monkeypatch, tmp_path):
    cfg = tmp_path / "presenter.json"
    cfg.write_text(
        '{"enabled": true, "installed": true, "has_cuda": false, "avatar_image": null}',
        encoding="utf-8",
    )
    monkeypatch.setattr("doctor.presenter_config_path", lambda: cfg)

    result = check_dependencies()

    assert result["presenter_enabled"] == "available"
    assert result["presenter_installed"] == "available"
    assert result["presenter_has_cuda"] == "unavailable"
    assert result["presenter_avatar"] == "not_configured"


def test_doctor_marks_absent_presenter_config_not_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "doctor.presenter_config_path", lambda: tmp_path / "presenter.json"
    )

    result = check_dependencies()

    assert {
        result["presenter_enabled"],
        result["presenter_installed"],
        result["presenter_has_cuda"],
        result["presenter_avatar"],
    } == {"not_configured"}

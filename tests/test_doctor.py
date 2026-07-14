from doctor import check_dependencies


def test_check_dependencies_returns_dict():
    result = check_dependencies()
    assert "python3" in result
    assert "ffmpeg" in result
    assert "screencapture" in result
    assert "selected_voice" in result
    assert result["python3"] in {"available", "unavailable"}
    assert result["screencapture"] in {"available", "unavailable"}

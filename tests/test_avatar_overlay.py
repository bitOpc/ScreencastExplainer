from pathlib import Path

from lib.avatar_overlay import build_pip_filter_complex


def test_pip_filter_contains_overlay_and_circle():
    ass = Path("/tmp/captions.ass")
    graph = build_pip_filter_complex(captions_ass=ass, width_ratio=0.18, margin_px=24)
    assert "ass=" in graph or "ass='" in graph
    assert "overlay=" in graph
    assert "[vout]" in graph
    assert "geq=" in graph or "alphamerge" in graph or "geq" in graph

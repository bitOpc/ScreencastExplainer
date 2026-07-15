import json
from pathlib import Path

import pytest

from lib.action_timeline import (
    Position,
    TargetRef,
    build_driver_call,
    load_action_timeline,
    resolve_position,
)


def write_actions(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_load_action_timeline_supports_single_target_and_sorts_events(tmp_path):
    path = write_actions(
        tmp_path / "actions.json",
        {
            "version": 1,
            "target": {"app_name": "Keynote", "title_contains": "Demo"},
            "events": [
                {"at": 4.0, "action": "key", "key": "right"},
                {"at": 1.0, "action": "wait"},
            ],
        },
    )

    timeline = load_action_timeline(path)

    assert timeline.targets == {
        "default": TargetRef(app_name="Keynote", title_contains="Demo")
    }
    assert [event.at for event in timeline.events] == [1.0, 4.0]
    assert timeline.events[1].target == "default"


def test_load_action_timeline_supports_multiple_targets(tmp_path):
    path = write_actions(
        tmp_path / "actions.json",
        {
            "version": 1,
            "targets": {
                "slides": {"app_name": "PowerPoint"},
                "browser": {"app_name": "Chrome", "title_contains": "Docs"},
            },
            "events": [
                {"at": 0, "target": "slides", "action": "key", "key": "right"},
                {
                    "at": 3.2,
                    "target": "browser",
                    "action": "scroll",
                    "direction": "down",
                },
            ],
        },
    )

    timeline = load_action_timeline(path)

    assert set(timeline.targets) == {"slides", "browser"}
    assert [event.target for event in timeline.events] == ["slides", "browser"]


def test_resolve_position_uses_window_relative_ratios():
    pos = resolve_position(Position(x_ratio=0.25, y_ratio=0.75), bounds=[100, 200, 800, 400])

    assert pos == (200, 300)


def test_resolve_position_supports_dict_bounds_from_cua_driver():
    bounds = {"x": 141.0, "y": 64.0, "width": 656.0, "height": 422.0}

    pos = resolve_position(Position(x_ratio=0.5, y_ratio=0.5), bounds=bounds)

    assert pos == (328, 211)


def test_build_driver_call_maps_key_and_hotkey():
    target = {"pid": 123, "window_id": 456, "bounds": [0, 0, 1000, 800]}

    key_call = build_driver_call(
        {"action": "key", "key": "right"},
        target,
    )
    hotkey_call = build_driver_call(
        {"action": "hotkey", "keys": "cmd+l"},
        target,
    )

    assert key_call.tool == "press_key"
    assert key_call.args == {
        "pid": 123,
        "key": "right",
        "delivery_mode": "background",
    }
    assert hotkey_call.tool == "hotkey"
    assert hotkey_call.args["keys"] == ["cmd", "l"]
    assert hotkey_call.args["delivery_mode"] == "background"


def test_build_driver_call_maps_pointer_and_scroll_actions():
    target = {"pid": 123, "window_id": 456, "bounds": [0, 0, 1000, 800]}

    click_call = build_driver_call(
        {
            "action": "click",
            "position": {"x_ratio": 0.5, "y_ratio": 0.25},
        },
        target,
    )
    double_call = build_driver_call(
        {
            "action": "double_click",
            "position": {"x": 20, "y": 30},
        },
        target,
    )
    scroll_call = build_driver_call(
        {
            "action": "scroll",
            "direction": "down",
            "amount": 4,
            "position": {"x_ratio": 0.5, "y_ratio": 0.5},
        },
        target,
    )

    assert click_call.tool == "click"
    assert click_call.args["x"] == 500
    assert click_call.args["y"] == 200
    assert click_call.args["window_id"] == 456
    assert double_call.tool == "double_click"
    assert double_call.args["x"] == 20
    assert double_call.args["y"] == 30
    assert scroll_call.tool == "scroll"
    assert scroll_call.args["direction"] == "down"
    assert scroll_call.args["amount"] == 4
    assert scroll_call.args["x"] == 500
    assert scroll_call.args["y"] == 400


def test_build_driver_call_rejects_foreground_delivery_by_default():
    target = {"pid": 123, "window_id": 456, "bounds": [0, 0, 1000, 800]}

    with pytest.raises(ValueError, match="foreground"):
        build_driver_call(
            {"action": "key", "key": "right", "delivery_mode": "foreground"},
            target,
        )

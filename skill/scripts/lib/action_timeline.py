"""通用 UI 动作时间轴模型与 cua-driver 调用映射。"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


ALLOWED_ACTIONS = {
    "wait",
    "key",
    "hotkey",
    "click",
    "double_click",
    "right_click",
    "scroll",
    "drag",
    "type_text",
}


@dataclass(frozen=True)
class TargetRef:
    app_name: str
    title_contains: str | None = None


@dataclass(frozen=True)
class Position:
    x: int | None = None
    y: int | None = None
    x_ratio: float | None = None
    y_ratio: float | None = None


@dataclass(frozen=True)
class ActionEvent:
    at: float
    action: str
    target: str = "default"
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ActionTimeline:
    version: int
    targets: dict[str, TargetRef]
    events: list[ActionEvent]


@dataclass(frozen=True)
class DriverCall:
    tool: str
    args: dict[str, Any]


def load_action_timeline(path: Path) -> ActionTimeline:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1:
        raise ValueError("actions.json version 必须为 1")
    targets = _parse_targets(data)
    events = [_parse_event(item, targets) for item in data.get("events", [])]
    if not events:
        raise ValueError("actions.json 至少需要一个 events 项")
    return ActionTimeline(
        version=1,
        targets=targets,
        events=sorted(events, key=lambda event: event.at),
    )


def _parse_targets(data: dict[str, Any]) -> dict[str, TargetRef]:
    if "targets" in data:
        raw_targets = data["targets"]
        if not isinstance(raw_targets, dict) or not raw_targets:
            raise ValueError("targets 必须是非空对象")
        return {name: _parse_target_ref(value) for name, value in raw_targets.items()}
    if "target" in data:
        return {"default": _parse_target_ref(data["target"])}
    raise ValueError("actions.json 必须包含 target 或 targets")


def _parse_target_ref(value: dict[str, Any]) -> TargetRef:
    app_name = value.get("app_name")
    if not isinstance(app_name, str) or not app_name:
        raise ValueError("target.app_name 必须是非空字符串")
    title_contains = value.get("title_contains")
    if title_contains is not None and not isinstance(title_contains, str):
        raise ValueError("target.title_contains 必须是字符串")
    return TargetRef(app_name=app_name, title_contains=title_contains)


def _parse_event(value: dict[str, Any], targets: dict[str, TargetRef]) -> ActionEvent:
    if not isinstance(value, dict):
        raise ValueError("event 必须是对象")
    at = float(value.get("at", 0.0))
    if at < 0:
        raise ValueError("event.at 不能为负数")
    action = value.get("action")
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"不支持的 action: {action}")
    target = value.get("target", "default")
    if target not in targets:
        raise ValueError(f"event.target 未声明: {target}")
    payload = {k: v for k, v in value.items() if k not in {"at", "action", "target"}}
    return ActionEvent(at=at, action=action, target=target, payload=payload)


def parse_position(value: dict[str, Any]) -> Position:
    if not isinstance(value, dict):
        raise ValueError("position 必须是对象")
    if "x" in value or "y" in value:
        if "x" not in value or "y" not in value:
            raise ValueError("position.x 与 position.y 必须同时提供")
        return Position(x=int(value["x"]), y=int(value["y"]))
    if "x_ratio" in value or "y_ratio" in value:
        if "x_ratio" not in value or "y_ratio" not in value:
            raise ValueError("position.x_ratio 与 position.y_ratio 必须同时提供")
        return Position(x_ratio=float(value["x_ratio"]), y_ratio=float(value["y_ratio"]))
    raise ValueError("position 必须包含 x/y 或 x_ratio/y_ratio")


def resolve_position(
    position: Position,
    bounds: list[int] | tuple[int, ...] | dict[str, Any] | None,
) -> tuple[int, int]:
    if position.x is not None and position.y is not None:
        return position.x, position.y
    if position.x_ratio is None or position.y_ratio is None:
        raise ValueError("position 缺少坐标")
    if not (0 <= position.x_ratio <= 1 and 0 <= position.y_ratio <= 1):
        raise ValueError("x_ratio/y_ratio 必须在 0..1 范围内")
    width, height = _bounds_size(bounds)
    return int(round(width * position.x_ratio)), int(round(height * position.y_ratio))


def _bounds_size(bounds: list[int] | tuple[int, ...] | dict[str, Any] | None) -> tuple[float, float]:
    """从 cua-driver bounds 提取 (width, height)。

    兼容两种格式：
    - dict：{"width", "height", "x", "y"}
    - list/tuple：[x, y, width, height]
    """
    if isinstance(bounds, dict):
        width = bounds.get("width")
        height = bounds.get("height")
        if width is None or height is None:
            raise ValueError("bounds 缺少 width/height")
        return float(width), float(height)
    if isinstance(bounds, (list, tuple)) and len(bounds) >= 4:
        return float(bounds[2]), float(bounds[3])
    raise ValueError("相对坐标需要目标窗口 bounds")


def build_driver_call(
    event: ActionEvent | dict[str, Any],
    target_window: dict[str, Any],
    *,
    allow_foreground: bool = False,
) -> DriverCall:
    action, payload = _event_action_and_payload(event)
    delivery_mode = payload.get("delivery_mode", "background")
    if delivery_mode == "foreground" and not allow_foreground:
        raise ValueError("默认禁止 foreground delivery_mode")
    if action == "wait":
        return DriverCall("wait", {"seconds": float(payload.get("seconds", 0.0))})

    base = {
        "pid": int(target_window["pid"]),
        "delivery_mode": delivery_mode,
    }
    window_id = target_window.get("window_id")

    if action == "key":
        return DriverCall("press_key", {**base, "key": _required_str(payload, "key")})
    if action == "hotkey":
        return DriverCall("hotkey", {**base, "keys": _parse_keys(payload.get("keys"))})
    if action == "type_text":
        return DriverCall("type_text", {**base, "text": _required_str(payload, "text")})
    if action in {"click", "double_click", "right_click"}:
        args = _pointer_args(payload, target_window, include_window=True)
        tool = "double_click" if action == "double_click" else "click"
        if action == "right_click":
            args["button"] = "right"
        return DriverCall(tool, {**base, **args})
    if action == "scroll":
        args = _optional_pointer_args(payload, target_window)
        args["direction"] = payload.get("direction", "down")
        args["amount"] = int(payload.get("amount", 3))
        if "by" in payload:
            args["by"] = payload["by"]
        if window_id is not None:
            args.setdefault("window_id", int(window_id))
        return DriverCall("scroll", {**base, **args})
    if action == "drag":
        return DriverCall("drag", {**base, **_drag_args(payload, target_window)})
    raise ValueError(f"不支持的 action: {action}")


def _event_action_and_payload(event: ActionEvent | dict[str, Any]) -> tuple[str, dict[str, Any]]:
    if isinstance(event, ActionEvent):
        return event.action, dict(event.payload)
    action = event.get("action")
    payload = {k: v for k, v in event.items() if k not in {"at", "action", "target"}}
    return str(action), payload


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"{key} 必须是非空字符串")
    return value


def _parse_keys(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part for part in value.replace("+", " ").split() if part]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("keys 必须是字符串或字符串数组")


def _pointer_args(
    payload: dict[str, Any],
    target_window: dict[str, Any],
    *,
    include_window: bool,
) -> dict[str, Any]:
    args: dict[str, Any] = {}
    if include_window and target_window.get("window_id") is not None:
        args["window_id"] = int(target_window["window_id"])
    if "element_index" in payload:
        args["element_index"] = int(payload["element_index"])
        return args
    if "element_token" in payload:
        args["element_token"] = payload["element_token"]
        return args
    if "position" in payload:
        x, y = resolve_position(parse_position(payload["position"]), target_window.get("bounds"))
        args["x"] = x
        args["y"] = y
        return args
    raise ValueError("指针动作必须提供 position、element_index 或 element_token")


def _optional_pointer_args(payload: dict[str, Any], target_window: dict[str, Any]) -> dict[str, Any]:
    if "position" not in payload and "element_index" not in payload and "element_token" not in payload:
        return {}
    return _pointer_args(payload, target_window, include_window=True)


def _drag_args(payload: dict[str, Any], target_window: dict[str, Any]) -> dict[str, Any]:
    if "from_position" not in payload or "to_position" not in payload:
        raise ValueError("drag 必须包含 from_position 与 to_position")
    from_x, from_y = resolve_position(parse_position(payload["from_position"]), target_window.get("bounds"))
    to_x, to_y = resolve_position(parse_position(payload["to_position"]), target_window.get("bounds"))
    args = {
        "from_x": from_x,
        "from_y": from_y,
        "to_x": to_x,
        "to_y": to_y,
    }
    if target_window.get("window_id") is not None:
        args["window_id"] = int(target_window["window_id"])
    return args

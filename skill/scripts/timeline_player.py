#!/usr/bin/env python3
"""按 actions.json 时间轴通过 cua-driver 回放 UI 动作。

正式录屏阶段使用本脚本直接驱动 cua-driver，避免 Agent 在录屏期间反复
调用 LLM `computer_use` 工具。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Protocol

# 保证可导入同目录 lib
_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from lib.action_timeline import (  # noqa: E402
    ActionTimeline,
    TargetRef,
    build_driver_call,
    load_action_timeline,
)


class Clock(Protocol):
    def now(self) -> float: ...
    def sleep(self, seconds: float) -> None: ...


class MonotonicClock:
    def now(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)


class CuaDriverCliClient:
    def __init__(self, driver_cmd: str = "cua-driver", *, timeout: float = 30.0):
        binary = shutil.which(driver_cmd) or driver_cmd
        self.driver_cmd = binary
        self.timeout = timeout

    def list_windows(self) -> list[dict[str, Any]]:
        result = self.call("list_windows", {"on_screen_only": True})
        return _extract_windows(result)

    def call(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        proc = subprocess.run(
            [self.driver_cmd, "call", tool, json.dumps(args, ensure_ascii=False)],
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"cua-driver call {tool} 失败（退出码 {proc.returncode}）: {proc.stderr.strip()}"
            )
        stdout = proc.stdout.strip()
        if not stdout:
            return {"ok": True}
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return {"ok": True, "output": stdout}
        if isinstance(data, dict):
            return data
        return {"ok": True, "result": data}


def play_timeline(
    timeline: ActionTimeline,
    *,
    client: Any,
    clock: Clock | None = None,
    dry_run: bool = False,
    allow_foreground: bool = False,
) -> dict[str, Any]:
    clock = clock or MonotonicClock()
    resolved_targets = resolve_targets(timeline, client)
    start = clock.now()
    planned: list[dict[str, Any]] = []
    executed = 0

    for event in timeline.events:
        target_window = resolved_targets[event.target]
        call = build_driver_call(
            event,
            target_window,
            allow_foreground=allow_foreground,
        )
        planned.append(
            {
                "at": event.at,
                "target": event.target,
                "action": event.action,
                "tool": call.tool,
                "args": call.args,
            }
        )
        if dry_run:
            continue
        due = start + event.at
        delay = max(0.0, due - clock.now())
        if delay:
            clock.sleep(delay)
        if call.tool == "wait":
            seconds = float(call.args.get("seconds", 0.0))
            if seconds > 0:
                clock.sleep(seconds)
        else:
            client.call(call.tool, call.args)
            executed += 1

    return {
        "status": "dry_run" if dry_run else "played",
        "events_planned": len(timeline.events),
        "events_executed": executed,
        "targets": resolved_targets,
        "planned": planned,
    }


def resolve_targets(timeline: ActionTimeline, client: Any) -> dict[str, dict[str, Any]]:
    windows = client.list_windows()
    resolved: dict[str, dict[str, Any]] = {}
    for name, target in timeline.targets.items():
        match = _find_window(windows, target)
        if match is None:
            raise RuntimeError(
                f"未找到目标窗口: {name} app_name={target.app_name!r} "
                f"title_contains={target.title_contains!r}"
            )
        resolved[name] = match
    return resolved


def _find_window(windows: list[dict[str, Any]], target: TargetRef) -> dict[str, Any] | None:
    app_name = target.app_name.lower()
    title_contains = target.title_contains.lower() if target.title_contains else None
    for window in windows:
        candidate_app = str(window.get("app_name", "")).lower()
        candidate_title = str(window.get("title", "")).lower()
        app_ok = app_name in candidate_app or candidate_app in app_name
        title_ok = title_contains is None or title_contains in candidate_title
        if app_ok and title_ok:
            return {
                "pid": window["pid"],
                "window_id": window.get("window_id"),
                "bounds": window.get("bounds"),
                "app_name": window.get("app_name"),
                "title": window.get("title"),
            }
    return None


def _extract_windows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("windows", "result"):
            if isinstance(value.get(key), list):
                return value[key]
        structured = value.get("structuredContent")
        if isinstance(structured, dict) and isinstance(structured.get("windows"), list):
            return structured["windows"]
    raise RuntimeError("cua-driver list_windows 输出中未找到 windows")


def main() -> None:
    parser = argparse.ArgumentParser(description="按 actions.json 回放通用 UI 动作时间轴")
    parser.add_argument("--actions", type=Path, required=True, help="actions.json 路径")
    parser.add_argument("--output-dir", type=Path, help="运行目录；用于默认报告路径")
    parser.add_argument("--driver-cmd", default="cua-driver", help="cua-driver 命令路径")
    parser.add_argument("--dry-run", action="store_true", help="只解析和规划，不执行动作")
    parser.add_argument(
        "--allow-foreground",
        action="store_true",
        help="允许 foreground delivery_mode（默认禁止）",
    )
    parser.add_argument("--report", type=Path, help="执行报告 JSON 路径")
    args = parser.parse_args()

    timeline = load_action_timeline(args.actions)
    client = CuaDriverCliClient(args.driver_cmd)
    report = play_timeline(
        timeline,
        client=client,
        dry_run=args.dry_run,
        allow_foreground=args.allow_foreground,
    )
    report_path = args.report
    if report_path is None and args.output_dir is not None:
        report_path = args.output_dir / "actions.report.json"
    if report_path is not None:
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

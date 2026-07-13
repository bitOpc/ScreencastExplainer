"""读写 run.json 与 segments.json。"""

import json
from typing import Any

from lib.paths import RunPaths


def load_segments(paths: RunPaths) -> dict[str, Any]:
    return json.loads(paths.segments_json.read_text(encoding="utf-8"))


def save_segments(paths: RunPaths, data: dict[str, Any]) -> None:
    paths.segments_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_run(paths: RunPaths) -> dict[str, Any]:
    return json.loads(paths.run_json.read_text(encoding="utf-8"))


def save_run(paths: RunPaths, data: dict[str, Any]) -> None:
    paths.run_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def update_run_status(paths: RunPaths, status: str) -> None:
    data = load_run(paths)
    data["status"] = status
    save_run(paths, data)

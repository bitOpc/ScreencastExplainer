from pathlib import Path

import pytest


@pytest.fixture
def tmp_run_dir(tmp_path: Path) -> Path:
    """创建最小运行目录结构。"""
    run_dir = tmp_path / "test-run"
    (run_dir / "capture").mkdir(parents=True)
    (run_dir / "video").mkdir(parents=True)
    return run_dir


@pytest.fixture
def sample_segments_draft() -> dict:
    return {
        "version": 1,
        "status": "draft",
        "segments": [
            {
                "id": 1,
                "text": "测试第一段旁白。",
                "expected_duration": 3.0,
                "page_target": "开头",
                "scroll_action": "none",
                "ui_target": "主区域",
            },
            {
                "id": 2,
                "text": "测试第二段旁白。",
                "expected_duration": 4.0,
                "page_target": "中段",
                "scroll_action": "scroll_down",
                "ui_target": "主区域",
            },
        ],
    }

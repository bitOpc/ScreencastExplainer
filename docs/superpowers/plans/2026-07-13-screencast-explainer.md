# Screencast Explainer 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `ScreencastExplainer` 仓库中实现可安装到 Hermes / Codex / Claude Code / OpenClaw 的 macOS 录屏讲解 skill，含 5 个 Python CLI 脚本与中文文档。

**Architecture:** 自包含 `skill/` 目录（SKILL.md + references + scripts），`install.sh` symlink 到四平台；Agent 用 Computer Use 录屏，Python 负责配音、字幕、合成。共享逻辑放在 `skill/scripts/lib/`。

**Tech Stack:** Python 3.10+、edge-tts、Pillow、ffmpeg/ffprobe、pytest

**设计依据:** `docs/superpowers/specs/2026-07-13-screencast-explainer-design.md`

**语言约定:** 文档与代码注释使用简体中文；标识符使用英文。

---

## 文件结构总览

| 文件 | 职责 |
|------|------|
| `skill/scripts/lib/paths.py` | `RunPaths` 数据类，解析 output-dir 下各路径 |
| `skill/scripts/lib/timefmt.py` | SRT/ASS 时间格式互转 |
| `skill/scripts/lib/subtitles.py` | 生成 `captions.srt` / `captions.ass` |
| `skill/scripts/lib/ffmpeg_util.py` | 查找 ffmpeg/ffprobe、探测时长、执行命令 |
| `skill/scripts/lib/run_state.py` | 读写 `run.json`、`segments.json` |
| `skill/scripts/doctor.py` | 依赖检查 CLI |
| `skill/scripts/init_run.py` | 初始化运行目录 CLI |
| `skill/scripts/build_narration.py` | Edge TTS 配音 + 字幕 CLI |
| `skill/scripts/ingest_capture.py` | 校验 raw.mp4 时长并标准化 CLI |
| `skill/scripts/compose_video.py` | 硬字幕合成 CLI |
| `install.sh` | 四平台 skill 安装/卸载 |
| `skill/SKILL.md` | Agent 强制工作流（中文） |
| `skill/references/*.md` | 参考文档（中文） |
| `tests/` | pytest 单元测试 |

---

### Task 1: 仓库骨架与测试环境

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `skill/scripts/lib/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: 创建 `.gitignore`**

```
outputs/
__pycache__/
*.pyc
.DS_Store
.venv/
.pytest_cache/
*.egg-info/
```

- [ ] **Step 2: 创建依赖文件**

`requirements.txt`:
```
edge-tts>=6.1.0
Pillow>=10.0.0
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest>=8.0.0
```

`pyproject.toml`:
```toml
[project]
name = "screencast-explainer"
version = "1.0.0"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["skill/scripts"]
testpaths = ["tests"]
```

- [ ] **Step 3: 创建 `tests/conftest.py`**

```python
import json
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
```

- [ ] **Step 4: 创建中文 `README.md` 骨架**

包含：项目简介、支持平台、快速开始（clone → pip install → install.sh → doctor）、目录结构、卸载说明。内容引用 spec，不重复全文。

- [ ] **Step 5: 安装开发依赖并验证 pytest**

```bash
cd /Users/alan/WorkSpace/ScreencastExplainer
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest --collect-only
```

Expected: `no tests ran` 或 `0 tests`（尚无测试文件）

- [ ] **Step 6: Commit**

```bash
git add .gitignore requirements.txt requirements-dev.txt pyproject.toml README.md skill/scripts/lib/__init__.py tests/
git commit -m "chore: 初始化仓库骨架与 pytest 环境"
```

---

### Task 2: 共享库 `paths` 与 `timefmt`

**Files:**
- Create: `skill/scripts/lib/paths.py`
- Create: `skill/scripts/lib/timefmt.py`
- Create: `tests/test_paths.py`
- Create: `tests/test_timefmt.py`

- [ ] **Step 1: 写失败测试 `tests/test_timefmt.py`**

```python
from lib.timefmt import ass_time, parse_srt_time, srt_time


def test_srt_roundtrip():
    assert srt_time(65.5) == "00:01:05,500"
    assert parse_srt_time("00:01:05,500") == 65.5


def test_ass_time():
    assert ass_time(65.5) == "0:01:05.50"
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_timefmt.py -v
```

Expected: `ModuleNotFoundError: No module named 'lib.timefmt'`

- [ ] **Step 3: 实现 `skill/scripts/lib/timefmt.py`**

```python
"""SRT 与 ASS 时间格式工具。"""


def srt_time(seconds: float) -> str:
    millis = int(round(seconds * 1000))
    h = millis // 3_600_000
    millis %= 3_600_000
    m = millis // 60_000
    millis %= 60_000
    s = millis // 1000
    ms = millis % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(millis) / 1000
    )


def ass_time(seconds: float) -> str:
    centis = int(round(seconds * 100))
    h = centis // 360_000
    centis %= 360_000
    m = centis // 6_000
    centis %= 6_000
    s = centis // 100
    cs = centis % 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"
```

- [ ] **Step 4: 写失败测试 `tests/test_paths.py`**

```python
from pathlib import Path

from lib.paths import RunPaths


def test_run_paths_resolve(tmp_path: Path):
    run_dir = tmp_path / "demo-run"
    paths = RunPaths(run_dir)
    assert paths.run_json == run_dir / "run.json"
    assert paths.segments_json == run_dir / "segments.json"
    assert paths.narration_wav == run_dir / "narration.wav"
    assert paths.raw_mp4 == run_dir / "capture" / "raw.mp4"
    assert paths.normalized_mp4 == run_dir / "video" / "normalized.mp4"
    assert paths.final_mp4 == run_dir / "video" / "final.mp4"
```

- [ ] **Step 5: 实现 `skill/scripts/lib/paths.py`**

```python
"""运行目录路径解析。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    root: Path

    @property
    def run_json(self) -> Path:
        return self.root / "run.json"

    @property
    def segments_json(self) -> Path:
        return self.root / "segments.json"

    @property
    def script_md(self) -> Path:
        return self.root / "script.md"

    @property
    def narration_wav(self) -> Path:
        return self.root / "narration.wav"

    @property
    def captions_srt(self) -> Path:
        return self.root / "captions.srt"

    @property
    def captions_ass(self) -> Path:
        return self.root / "captions.ass"

    @property
    def capture_dir(self) -> Path:
        return self.root / "capture"

    @property
    def raw_mp4(self) -> Path:
        return self.capture_dir / "raw.mp4"

    @property
    def video_dir(self) -> Path:
        return self.root / "video"

    @property
    def normalized_mp4(self) -> Path:
        return self.video_dir / "normalized.mp4"

    @property
    def final_mp4(self) -> Path:
        return self.video_dir / "final.mp4"

    @property
    def work_audio_dir(self) -> Path:
        return self.root / "workaudio"

    def ensure_dirs(self) -> None:
        """创建运行所需子目录。"""
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.work_audio_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 6: 运行测试**

```bash
pytest tests/test_paths.py tests/test_timefmt.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add skill/scripts/lib/paths.py skill/scripts/lib/timefmt.py tests/test_paths.py tests/test_timefmt.py
git commit -m "feat: 添加 paths 与 timefmt 共享库"
```

---

### Task 3: 共享库 `subtitles`、`ffmpeg_util`、`run_state`

**Files:**
- Create: `skill/scripts/lib/subtitles.py`
- Create: `skill/scripts/lib/ffmpeg_util.py`
- Create: `skill/scripts/lib/run_state.py`
- Create: `tests/test_subtitles.py`
- Create: `tests/test_run_state.py`

- [ ] **Step 1: 写 `tests/test_subtitles.py`**

```python
from pathlib import Path

from lib.subtitles import write_subtitles


def test_write_subtitles_creates_srt_and_ass(tmp_path: Path):
    timings = [
        {"start": 0.0, "end": 2.5, "text": "你好世界"},
        {"start": 2.5, "end": 5.0, "text": "第二句字幕"},
    ]
    srt_path = tmp_path / "captions.srt"
    ass_path = tmp_path / "captions.ass"
    write_subtitles(timings, srt_path, ass_path)
    srt_text = srt_path.read_text(encoding="utf-8")
    ass_text = ass_path.read_text(encoding="utf-8")
    assert "你好世界" in srt_text
    assert "00:00:00,000 --> 00:00:02,500" in srt_text
    assert "[Script Info]" in ass_text
    assert "Dialogue:" in ass_text
```

- [ ] **Step 2: 实现 `skill/scripts/lib/subtitles.py`**

从 `/Users/alan/Documents/视频处理/tools/build_obsidian_llm_explainer.py` 迁移 `visual_width`、`wrap_ass_text`、`write_subtitles`，import 改为 `from lib.timefmt import ass_time, srt_time`。文件头注释：`"""生成 SRT 与 ASS 硬字幕文件。"""`

- [ ] **Step 3: 写 `tests/test_run_state.py`**

```python
import json

from lib.paths import RunPaths
from lib.run_state import load_segments, save_run, save_segments


def test_save_and_load_segments(tmp_run_dir, sample_segments_draft):
    paths = RunPaths(tmp_run_dir)
    save_segments(paths, sample_segments_draft)
    loaded = load_segments(paths)
    assert loaded["status"] == "draft"
    assert len(loaded["segments"]) == 2


def test_save_run(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    save_run(paths, {"run_id": "demo", "status": "initialized"})
    data = json.loads(paths.run_json.read_text(encoding="utf-8"))
    assert data["run_id"] == "demo"
```

- [ ] **Step 4: 实现 `skill/scripts/lib/run_state.py`**

```python
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
```

- [ ] **Step 5: 实现 `skill/scripts/lib/ffmpeg_util.py`**

```python
"""ffmpeg / ffprobe 工具函数。"""

import shutil
import subprocess
from pathlib import Path


def ffmpeg_path() -> str:
    candidates = [
        "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
        "/opt/homebrew/bin/ffmpeg",
        "ffmpeg",
    ]
    for candidate in candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise FileNotFoundError("未找到 ffmpeg，请运行: brew install ffmpeg")


def ffprobe_path() -> str:
    candidates = [
        "/opt/homebrew/opt/ffmpeg-full/bin/ffprobe",
        "/opt/homebrew/bin/ffprobe",
        "ffprobe",
    ]
    for candidate in candidates:
        if Path(candidate).exists() or shutil.which(candidate):
            return candidate
    raise FileNotFoundError("未找到 ffprobe，请运行: brew install ffmpeg")


def probe_duration(path: Path) -> float:
    """用 ffprobe 读取媒体文件时长（秒）。"""
    output = subprocess.run(
        [
            ffprobe_path(),
            "-hide_banner",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    return float(output.stdout.strip())


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run([ffmpeg_path(), *args], check=True)
```

- [ ] **Step 6: 运行测试**

```bash
pytest tests/test_subtitles.py tests/test_run_state.py -v
```

Expected: 全部 PASS

- [ ] **Step 7: Commit**

```bash
git add skill/scripts/lib/subtitles.py skill/scripts/lib/ffmpeg_util.py skill/scripts/lib/run_state.py tests/
git commit -m "feat: 添加 subtitles、ffmpeg_util、run_state 共享库"
```

---

### Task 4: `doctor.py`

**Files:**
- Create: `skill/scripts/doctor.py`
- Create: `tests/test_doctor.py`

- [ ] **Step 1: 写 `tests/test_doctor.py`**

```python
from doctor import check_dependencies


def test_check_dependencies_returns_dict():
    result = check_dependencies()
    assert "python3" in result
    assert "ffmpeg" in result
    assert "selected_voice" in result
    assert result["python3"] in {"available", "unavailable"}
```

- [ ] **Step 2: 运行确认失败**

```bash
pytest tests/test_doctor.py -v
```

- [ ] **Step 3: 实现 `skill/scripts/doctor.py`**

```python
#!/usr/bin/env python3
"""依赖检查：ffmpeg、ffprobe、edge-tts、中文字体。"""

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import ImageFont

DEFAULT_VOICE_ID = "zh-CN-YunxiNeural"
DEFAULT_VOICE_RATE = "-3%"


def _available(binary: str) -> bool:
    return shutil.which(binary) is not None


def _edge_tts_available() -> bool:
    return importlib.util.find_spec("edge_tts") is not None


def _cjk_font_available() -> bool:
    candidates = [
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                ImageFont.truetype(path, 24)
                return True
            except OSError:
                continue
    return False


def check_dependencies() -> dict[str, str]:
    edge = _edge_tts_available()
    return {
        "python3": "available",
        "ffmpeg": "available" if _available("ffmpeg") else "unavailable",
        "ffprobe": "available" if _available("ffprobe") else "unavailable",
        "edge_tts": "available" if edge else "unavailable",
        "cjk_font": "available" if _cjk_font_available() else "unavailable",
        "selected_voice": DEFAULT_VOICE_ID if edge else "unavailable",
        "selected_voice_rate": DEFAULT_VOICE_RATE if edge else "unavailable",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="检查 Screencast Explainer 依赖")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()
    result = check_dependencies()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for key, value in result.items():
            print(f"{key}: {value}")
    required = ["ffmpeg", "ffprobe", "edge_tts"]
    if any(result[k] == "unavailable" for k in required):
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 运行测试与手动验证**

```bash
pytest tests/test_doctor.py -v
python3 skill/scripts/doctor.py
python3 skill/scripts/doctor.py --json
```

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/doctor.py tests/test_doctor.py
git commit -m "feat: 添加 doctor.py 依赖检查"
```

---

### Task 5: `init_run.py`

**Files:**
- Create: `skill/scripts/init_run.py`
- Create: `tests/test_init_run.py`

- [ ] **Step 1: 写 `tests/test_init_run.py`**

```python
import json
from datetime import datetime

from init_run import init_run
from lib.paths import RunPaths


def test_init_run_creates_structure(tmp_path):
    run_dir = tmp_path / "20260713-demo"
    init_run(
        RunPaths(run_dir),
        voice_id="zh-CN-YunxiNeural",
        voice_rate="-3%",
        run_id="20260713-demo",
    )
    paths = RunPaths(run_dir)
    assert paths.capture_dir.is_dir()
    assert paths.video_dir.is_dir()
    data = json.loads(paths.run_json.read_text(encoding="utf-8"))
    assert data["status"] == "initialized"
    assert data["voice_id"] == "zh-CN-YunxiNeural"
```

- [ ] **Step 2: 实现 `skill/scripts/init_run.py`**

```python
#!/usr/bin/env python3
"""初始化一次讲解视频运行的输出目录。"""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from lib.paths import RunPaths
from lib.run_state import save_run

DEFAULT_VOICE_ID = "zh-CN-YunxiNeural"
DEFAULT_VOICE_RATE = "-3%"


def init_run(
    paths: RunPaths,
    *,
    voice_id: str,
    voice_rate: str,
    run_id: str,
    target_description: str = "",
) -> None:
    paths.ensure_dirs()
    save_run(
        paths,
        {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "initialized",
            "voice_provider": "Edge TTS",
            "voice_id": voice_id,
            "voice_rate": voice_rate,
            "voice_style": "中文自然男声",
            "target_description": target_description,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化讲解视频运行目录")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--voice-id", default=DEFAULT_VOICE_ID)
    parser.add_argument("--voice-rate", default=DEFAULT_VOICE_RATE)
    parser.add_argument("--target-description", default="")
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    init_run(
        paths,
        voice_id=args.voice_id,
        voice_rate=args.voice_rate,
        run_id=paths.root.name,
        target_description=args.target_description,
    )
    print(f"已初始化: {paths.root}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/test_init_run.py -v
```

- [ ] **Step 4: Commit**

```bash
git add skill/scripts/init_run.py tests/test_init_run.py
git commit -m "feat: 添加 init_run.py 运行目录初始化"
```

---

### Task 6: `build_narration.py`

**Files:**
- Create: `skill/scripts/build_narration.py`
- Create: `tests/test_build_narration.py`

- [ ] **Step 1: 写测试（mock edge_tts）**

```python
from unittest.mock import AsyncMock, patch

import pytest

from build_narration import build_narration_timings
from lib.paths import RunPaths
from lib.run_state import load_segments, save_segments


@pytest.mark.asyncio
async def test_build_narration_updates_segments(tmp_run_dir, sample_segments_draft):
    paths = RunPaths(tmp_run_dir)
    save_segments(paths, sample_segments_draft)

    async def fake_synthesize(text, output, voice, rate):
        # 写入最小合法 wav 头由 ffmpeg 处理；此处只测时间轴逻辑
        output.write_bytes(b"\x00")

    with patch("build_narration.synthesize_clip", new=AsyncMock(side_effect=fake_synthesize)):
        with patch("build_narration.concat_audio", return_value=None):
            with patch("build_narration.wav_duration", return_value=3.0):
                timings = await build_narration_timings(
                    paths, voice_id="zh-CN-YunxiNeural", voice_rate="-3%", gap=0.45
                )
    assert len(timings) == 2
    data = load_segments(paths)
    assert data["status"] == "narrated"
    assert "start" in data["segments"][0]
```

若项目暂不引入 `pytest-asyncio`，可改为将核心逻辑拆为同步函数 `build_narration_sync` 并用 `asyncio.run` 包装 CLI。

- [ ] **Step 2: 实现 `skill/scripts/build_narration.py`**

核心逻辑：
1. 读取 `segments.json`，要求 `status == "draft"`
2. 对每段调用 `edge_tts` 合成 clip
3. 用 `expected_duration` + `gap` 累加计算 `start`/`end`（秒），再格式化为 SRT 字符串写入 segment
4. ffmpeg concat 为 `narration.wav`
5. 调用 `write_subtitles` 写 srt/ass
6. 更新 `status: narrated`，`update_run_status(paths, "narrated")`

时间轴算法（draft 阶段无 start/end）：

```python
cursor = 0.0
for seg in segments:
    seg["start"] = srt_time(cursor)
    duration = seg["expected_duration"]
    cursor += duration
    seg["end"] = srt_time(cursor)
    seg["actual_duration"] = duration
    cursor += gap
```

TTS 后可用真实 clip 时长覆盖 `actual_duration` 并重新计算后续时间轴（与旧 `edge_narrate.py` 对齐：以实际音频时长为准）。

- [ ] **Step 3: 添加 `pytest-asyncio` 到 `requirements-dev.txt` 或改用同步测试**

`requirements-dev.txt` 增加 `pytest-asyncio>=0.23.0`，`pyproject.toml` 增加 `asyncio_mode = "auto"`。

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_build_narration.py -v
```

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/build_narration.py tests/test_build_narration.py requirements-dev.txt pyproject.toml
git commit -m "feat: 添加 build_narration.py 配音与字幕生成"
```

---

### Task 7: `ingest_capture.py`

**Files:**
- Create: `skill/scripts/ingest_capture.py`
- Create: `tests/test_ingest_capture.py`

- [ ] **Step 1: 写测试**

```python
from unittest.mock import patch

import pytest

from ingest_capture import validate_av_duration
from lib.paths import RunPaths


def test_validate_av_duration_within_tolerance():
    validate_av_duration(video_duration=60.0, audio_duration=60.3, tolerance=0.5)


def test_validate_av_duration_raises():
    with pytest.raises(ValueError, match="音画时长偏差"):
        validate_av_duration(video_duration=50.0, audio_duration=60.0, tolerance=0.5)
```

- [ ] **Step 2: 实现 `skill/scripts/ingest_capture.py`**

```python
def validate_av_duration(
    *, video_duration: float, audio_duration: float, tolerance: float = 0.5
) -> None:
    delta = abs(video_duration - audio_duration)
    if delta > tolerance:
        raise ValueError(
            f"音画时长偏差过大: 视频 {video_duration:.2f}s, 旁白 {audio_duration:.2f}s, "
            f"偏差 {delta:.2f}s（允许 ±{tolerance}s）。请重新录屏或调整旁白后重试。"
        )
```

`main()` 流程：
1. 检查 `capture/raw.mp4` 存在
2. `probe_duration` 分别读 raw.mp4 与 narration.wav
3. `validate_av_duration`
4. ffmpeg 复制或重编码到 `video/normalized.mp4`（`-c copy` 优先，失败则 libx264）
5. `update_run_status(paths, "ingested")`

- [ ] **Step 3: 运行测试**

```bash
pytest tests/test_ingest_capture.py -v
```

- [ ] **Step 4: Commit**

```bash
git add skill/scripts/ingest_capture.py tests/test_ingest_capture.py
git commit -m "feat: 添加 ingest_capture.py 录屏导入与时长校验"
```

---

### Task 8: `compose_video.py`

**Files:**
- Create: `skill/scripts/compose_video.py`
- Create: `tests/test_compose_video.py`

- [ ] **Step 1: 写测试（mock ffmpeg）**

```python
from unittest.mock import patch
from pathlib import Path

from compose_video import build_mux_command
from lib.paths import RunPaths


def test_build_mux_command(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.normalized_mp4.write_bytes(b"x")
    paths.narration_wav.write_bytes(b"x")
    paths.captions_ass.write_bytes(b"x")
    cmd = build_mux_command(paths, crf=18)
    assert "-filter_complex" in cmd
    assert "ass=" in " ".join(cmd)
```

- [ ] **Step 2: 实现 `skill/scripts/compose_video.py`**

从 `record_obsidian_live_llm.py` 迁移 `mux` 为 `build_mux_command` + `compose_video(paths, crf)`。ASS 路径含特殊字符时用 `ass='...'` 转义。

`main()` 检查输入文件存在 → 调用 compose → `update_run_status(paths, "composed")` → 打印 `final.mp4` 路径。

- [ ] **Step 3: 运行测试**

```bash
pytest tests/test_compose_video.py -v
```

- [ ] **Step 4: Commit**

```bash
git add skill/scripts/compose_video.py tests/test_compose_video.py
git commit -m "feat: 添加 compose_video.py 硬字幕合成"
```

---

### Task 9: `install.sh`

**Files:**
- Create: `install.sh`

- [ ] **Step 1: 实现 `install.sh`**

 Bash 脚本，中文注释。支持 `--platform`、`--hermes-profile`（默认 `ailearn`）、`--dry-run`、`--force`、`--uninstall`、`-h`。

核心函数 `install_platform(name, target)`：
- `mkdir -p "$(dirname "$target")"`
- 若 `$target` 已是正确 symlink → 跳过
- 若存在且非 symlink 且无 `--force` → 报错
- `ln -sfn "$SKILL_SRC" "$target"`

平台映射：
```bash
HERMES_TARGET="$HOME/.hermes/profiles/${HERMES_PROFILE}/skills/screencast-explainer"
CODEX_TARGET="$HOME/.codex/skills/screencast-explainer"
CLAUDE_TARGET="$HOME/.claude/skills/screencast-explainer"
OPENCLAW_TARGET="$HOME/.agents/skills/screencast-explainer"
```

`--uninstall`：仅当 symlink 目标解析为当前仓库 `skill/` 时 `rm` 该 symlink。

- [ ] **Step 2: 手动验证**

```bash
chmod +x install.sh
./install.sh --dry-run
./install.sh --platform codex --dry-run
```

Expected: 打印四条 ln -sfn 命令，不实际执行

- [ ] **Step 3: Commit**

```bash
git add install.sh
git commit -m "feat: 添加 install.sh 四平台 skill 安装脚本"
```

---

### Task 10: `SKILL.md` 与 reference 文档

**Files:**
- Create: `skill/SKILL.md`
- Create: `skill/references/standard-pipeline.md`
- Create: `skill/references/voice-presets.md`
- Create: `skill/references/failure-modes.md`
- Create: `skill/references/segment-schema.md`
- Create: `skill/references/install-paths.md`

- [ ] **Step 1: 编写 `skill/SKILL.md`**

- frontmatter 按 spec 第 6 节（中文 description）
- 正文包含强制工作流步骤 0–9（中文）
- 脚本调用使用 `<skill-root>/scripts/...` 占位说明
- 交付格式清单（无抽帧验收）
- 引用 `references/` 各文件

可参考并改写 `/Users/alan/Documents/视频处理/outputs/hermes_obsidian_skillkit/skill_variant/SKILL.md`，删除连续采帧与 Hermes 专属措辞，改为通用四平台表述。

- [ ] **Step 2: 编写五篇 reference（全文中文）**

| 文件 | 内容要点 |
|------|----------|
| `standard-pipeline.md` | Computer Use + Python + ffmpeg 三段式职责 |
| `voice-presets.md` | 默认 YunxiNeural -3%，可配置字段说明 |
| `failure-modes.md` | spec 中 4 类失败模式与处理 |
| `segment-schema.md` | segments.json draft/narrated 字段表与示例 |
| `install-paths.md` | 四平台路径与 install.sh 用法 |

- [ ] **Step 3: 更新 `README.md`**

补充完整快速开始、工作流简表、文档链接。

- [ ] **Step 4: Commit**

```bash
git add skill/SKILL.md skill/references/ README.md
git commit -m "docs: 添加 SKILL.md 与中文参考文档"
```

---

### Task 11: 端到端冒烟验证

**Files:**
- Modify: `README.md`（追加验证章节）

- [ ] **Step 1: 安装 skill**

```bash
./install.sh --platform codex --dry-run   # 确认无误后
./install.sh
pip install -r requirements.txt
```

- [ ] **Step 2: 跑通 Python 流水线（无需真实录屏）**

```bash
RUN=outputs/smoke-$(date +%Y%m%d-%H%M%S)
python3 skill/scripts/doctor.py
python3 skill/scripts/init_run.py --output-dir "$RUN"

# 写入测试 segments.json 与 script.md
# 运行 build_narration.py（需网络调用 Edge TTS）

# 用 ffmpeg 生成静音占位 raw.mp4，时长与 narration.wav 一致
AUDIO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RUN/narration.wav")
ffmpeg -y -f lavfi -i color=c=black:s=1920x1080:d=$AUDIO_DUR -pix_fmt yuv420p "$RUN/capture/raw.mp4"

python3 skill/scripts/ingest_capture.py --output-dir "$RUN"
python3 skill/scripts/compose_video.py --output-dir "$RUN"
```

Expected: `$RUN/video/final.mp4` 存在且可播放

- [ ] **Step 3: 运行全量单元测试**

```bash
pytest -v
```

Expected: 全部 PASS

- [ ] **Step 4: 在 README 记录冒烟步骤并 Commit**

```bash
git add README.md
git commit -m "docs: 添加端到端冒烟验证说明"
```

---

## Spec 覆盖自检

| Spec 要求 | 对应 Task |
|-----------|-----------|
| skill 自包含目录 | Task 1, 10 |
| 5 个 CLI 脚本 | Task 4–8 |
| segments.json 两阶段 | Task 3, 6, `segment-schema.md` |
| 仅实时录屏 | Task 7, SKILL 步骤 7 |
| 无 verify_keyframes | 未创建该脚本 |
| install.sh 四平台 | Task 9 |
| 中文文档与注释 | 全任务 |
| 从视频处理/tools 迁移 | Task 3, 6, 8 注明迁移来源 |
| 默认声音 YunxiNeural | Task 4, `voice-presets.md` |

## 执行方式

计划已保存。可选两种执行方式：

**1. Subagent-Driven（推荐）** — 每个 Task 派发独立子代理，任务间做审查，迭代更快

**2. Inline Execution** — 在本会话按 Task 顺序直接实现，分批检查点确认

你想用哪种方式？

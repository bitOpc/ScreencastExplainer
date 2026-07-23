# Presenter Avatar（真人讲解）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Screencast Explainer 增加可选的本地 SadTalker 真人讲解画中画：安装/成片双重确认、分段生成口型视频、右下角圆形叠加。

**Architecture:** 全局配置在 `~/.screencast-explainer/presenter.json`；本片状态在 `$RUN/avatar.json`。`install_presenter.sh` 独立安装 SadTalker。`build_avatar.py` 按旁白分段调用本地 `inference.py` 并拼接无音轨 `video/avatar.mp4`。`compose_video.py` 在本片启用时把 avatar 圆形叠到字幕之上。Agent 剧本写在 `docs/install.md` 与 `SKILL.md`，脚本不代替用户确认。

**Tech Stack:** Python 3.10+、ffmpeg、本地 SadTalker（独立 venv）、pytest、bash

**设计依据:** [`docs/presenter-avatar-design.md`](presenter-avatar-design.md)

## Global Constraints

- 仅真人半身照；不支持卡通
- 仅本地 SadTalker；不接云端 API
- 禁止静默安装 / 跳过无 GPU 确认 / 无半身照占位生成
- 主 skill 不依赖本能力；SadTalker 不进主 venv
- 文档与代码注释使用简体中文；标识符英文
- 平台：macOS（主 skill）；SadTalker 本地可在有/无 CUDA 下安装（无 CUDA 须强警告）

## File Structure

| 文件 | 职责 |
|------|------|
| `skill/scripts/lib/presenter_config.py` | 读写 `presenter.json`、默认配置、半身照落盘、耗时估算 |
| `skill/scripts/lib/avatar_overlay.py` | 构建圆形 PiP 的 ffmpeg `filter_complex` |
| `skill/scripts/lib/paths.py` | 增加 `avatar_json` / `avatar_mp4` / `avatar_report_json` |
| `scripts/install_presenter.sh` | 克隆 SadTalker、venv、权重、写 `presenter.json` |
| `skill/scripts/build_avatar.py` | 分段调用 SadTalker → 拼接 `video/avatar.mp4` |
| `skill/scripts/compose_video.py` | 可选 PiP 分支 |
| `skill/scripts/doctor.py` | 可选 `presenter` 状态（不阻断） |
| `skill/references/presenter-avatar.md` | Agent 参考：确认剧本、估算、照片要求、CLI |
| `docs/install.md` / `docs/update.md` / `SKILL.md` / README | 安装与使用剧本 |

---

### Task 1: Presenter 配置库与 RunPaths

**Files:**
- Create: `skill/scripts/lib/presenter_config.py`
- Modify: `skill/scripts/lib/paths.py`
- Test: `tests/test_presenter_config.py`、`tests/test_paths.py`

**Interfaces:**
- Produces:
  - `CONFIG_DIR = Path.home() / ".screencast-explainer"`
  - `presenter_config_path() -> Path`
  - `default_presenter_config() -> dict`
  - `load_presenter_config(path: Path | None = None) -> dict`
  - `save_presenter_config(data: dict, path: Path | None = None) -> None`
  - `estimate_avatar_minutes(audio_seconds: float, *, has_cuda: bool) -> dict`  
    返回 `{"label": str, "min_minutes": float | None, "max_minutes": float | None, "needs_slow_confirm": bool}`
  - `install_avatar_image(src: Path, dest: Path | None = None) -> Path`  
    复制到 `~/.screencast-explainer/avatars/default.png`（或指定 dest），校验后缀 `.jpg/.jpeg/.png`
  - `RunPaths.avatar_json` → `root / "avatar.json"`
  - `RunPaths.avatar_mp4` → `video_dir / "avatar.mp4"`
  - `RunPaths.avatar_report_json` → `video_dir / "avatar.report.json"`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_presenter_config.py
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
    assert result["min_minutes"] == 20.0  # 600*2/60
    assert result["max_minutes"] == 40.0  # 600*4/60


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
```

在 `tests/test_paths.py` 追加：

```python
def test_avatar_paths(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    assert paths.avatar_json == tmp_run_dir / "avatar.json"
    assert paths.avatar_mp4 == tmp_run_dir / "video" / "avatar.mp4"
    assert paths.avatar_report_json == tmp_run_dir / "video" / "avatar.report.json"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_presenter_config.py tests/test_paths.py::test_avatar_paths -v`  
Expected: FAIL（模块或属性不存在）

- [ ] **Step 3: 实现 `presenter_config.py` 与 paths 属性**

`estimate_avatar_minutes`：
- CUDA：`min = audio_seconds * 2 / 60`，`max = audio_seconds * 4 / 60`，`label` 含区间
- 非 CUDA：`min_minutes/max_minutes = None`，`needs_slow_confirm=True`，`label` 含「可能数小时」

`install_avatar_image`：后缀不在 `{.jpg,.jpeg,.png,.JPG,.JPEG,.PNG}` 时 `raise ValueError`；`dest.parent.mkdir(parents=True)`；`shutil.copy2`。

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_presenter_config.py tests/test_paths.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/lib/presenter_config.py skill/scripts/lib/paths.py \
  tests/test_presenter_config.py tests/test_paths.py
git commit -m "$(cat <<'EOF'
feat: 增加 presenter 配置库与 avatar 路径

EOF
)"
```

---

### Task 2: 圆形 PiP filter + compose 分支

**Files:**
- Create: `skill/scripts/lib/avatar_overlay.py`
- Modify: `skill/scripts/compose_video.py`
- Test: `tests/test_avatar_overlay.py`、`tests/test_compose_video.py`

**Interfaces:**
- Consumes: `RunPaths`；可选读 `$RUN/avatar.json` 的 `use_presenter`
- Produces:
  - `build_pip_filter_complex(*, captions_ass: Path, width_ratio: float = 0.18, margin_px: int = 24) -> str`  
    输入约定：`[0:v]` 主画面，`[1:v]` avatar，`[2:a]` 旁白（由 compose 命令映射）  
    输出标签：`[vout]`  
    顺序：主画面 ass 字幕 → 缩放 avatar → 圆形 alpha → overlay 右下角（字幕之上）
  - `build_mux_command(paths, *, crf=18, with_avatar: bool | None = None) -> list[str]`  
    `with_avatar is None`：若 `avatar.json` 存在且 `use_presenter` 且 `avatar_mp4` 存在则为 True  
    `with_avatar=False` 或文件缺失：保持现有双输入命令

- [ ] **Step 1: 写失败测试**

```python
# tests/test_avatar_overlay.py
from pathlib import Path

from lib.avatar_overlay import build_pip_filter_complex


def test_pip_filter_contains_overlay_and_circle():
    ass = Path("/tmp/captions.ass")
    graph = build_pip_filter_complex(captions_ass=ass, width_ratio=0.18, margin_px=24)
    assert "ass=" in graph or "ass='" in graph
    assert "overlay=" in graph
    assert "[vout]" in graph
    assert "geq=" in graph or "alphamerge" in graph or "geq" in graph
```

```python
# tests/test_compose_video.py 追加
def test_build_mux_command_with_avatar(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.normalized_mp4.write_bytes(b"x")
    paths.narration_wav.write_bytes(b"x")
    paths.captions_ass.write_bytes(b"x")
    paths.video_dir.mkdir(parents=True, exist_ok=True)
    paths.avatar_mp4.write_bytes(b"x")
    paths.avatar_json.write_text(
        '{"use_presenter": true, "source_image": "a.png", '
        '"estimated_seconds": 10, "user_confirmed_slow": true}',
        encoding="utf-8",
    )
    cmd = build_mux_command(paths, crf=18, with_avatar=True)
    assert str(paths.avatar_mp4) in cmd
    assert cmd.count("-i") >= 3


def test_build_mux_command_skips_avatar_when_disabled(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.normalized_mp4.write_bytes(b"x")
    paths.narration_wav.write_bytes(b"x")
    paths.captions_ass.write_bytes(b"x")
    paths.video_dir.mkdir(parents=True, exist_ok=True)
    paths.avatar_mp4.write_bytes(b"x")
    cmd = build_mux_command(paths, crf=18, with_avatar=False)
    assert str(paths.avatar_mp4) not in cmd
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_avatar_overlay.py tests/test_compose_video.py -v`  
Expected: 新测试 FAIL

- [ ] **Step 3: 实现 overlay 与 compose 分支**

推荐 `filter_complex` 骨架（可微调，但测试断言的关键字须保留）：

```text
[0:v]ass=...[base];
[1:v]scale=iw*0.18:-1,format=rgba,
geq=lum='p(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),min(W,H)/2),255,0)'[pip];
[base][pip]overlay=main_w-overlay_w-24:main_h-overlay_h-24[vout]
```

`with_avatar=True` 时输入顺序：`normalized` → `avatar` → `narration`；`-map [vout] -map 2:a:0`。

CLI 增加 `--with-avatar` / `--no-avatar`（可选覆盖自动探测）。

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_avatar_overlay.py tests/test_compose_video.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/lib/avatar_overlay.py skill/scripts/compose_video.py \
  tests/test_avatar_overlay.py tests/test_compose_video.py
git commit -m "$(cat <<'EOF'
feat: compose 支持圆形右下角 avatar 叠加

EOF
)"
```

---

### Task 3: build_avatar.py（分段 SadTalker + 拼接）

**Files:**
- Create: `skill/scripts/build_avatar.py`
- Test: `tests/test_build_avatar.py`

**Interfaces:**
- Consumes: `RunPaths`、`avatar.json`、`workaudio/edge_clips/clip_*.wav`、`presenter.json`（sadtalker 参数）
- Produces:
  - `load_run_avatar(paths: RunPaths) -> dict`
  - `list_narration_clips(paths: RunPaths) -> list[Path]`（按 `clip_001.wav` 排序）
  - `run_sadtalker_segment(*, python: Path, sadtalker_root: Path, source_image: Path, audio: Path, out_mp4: Path, still: bool, preprocess: str, face_model_resolution: int) -> None`  
    调用：`{python} inference.py --driven_audio ... --source_image ... --result_dir ... --still --preprocess full`（按配置），再把结果文件复制/转为 `out_mp4`
  - `concat_avatar_clips(clip_mp4s: list[Path], gap_seconds: float, output: Path) -> None`  
    段间插入静止帧（取上一段末帧）对齐 gap；输出无音轨
  - `build_avatar(paths: RunPaths, *, presenter_cfg: dict | None = None) -> Path`  
    要求 `avatar.json.use_presenter is True` 且 `source_image` 文件存在；否则 `raise ValueError`  
    写 `avatar.report.json`：`{"segments":[{"id":1,"status":"ok"|"failed","seconds":...}], "output": "..."}`  
    任一段失败：`raise RuntimeError`（不静默跳过）；报告已写盘

- [ ] **Step 1: 写失败测试（mock subprocess）**

```python
# tests/test_build_avatar.py
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from build_avatar import build_avatar, list_narration_clips, load_run_avatar
from lib.paths import RunPaths


def test_list_narration_clips_sorted(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    clips = paths.work_audio_dir / "edge_clips"
    clips.mkdir(parents=True)
    (clips / "clip_002.wav").write_bytes(b"x")
    (clips / "clip_001.wav").write_bytes(b"x")
    found = list_narration_clips(paths)
    assert [p.name for p in found] == ["clip_001.wav", "clip_002.wav"]


def test_build_avatar_requires_confirmation(tmp_run_dir):
    paths = RunPaths(tmp_run_dir)
    paths.avatar_json.write_text(
        json.dumps({"use_presenter": False, "source_image": "a.png"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="use_presenter"):
        build_avatar(paths)


def test_build_avatar_calls_sadtalker_per_clip(tmp_run_dir, tmp_path):
    paths = RunPaths(tmp_run_dir)
    paths.ensure_dirs()
    photo = tmp_path / "face.png"
    photo.write_bytes(b"img")
    paths.avatar_json.write_text(
        json.dumps(
            {
                "use_presenter": True,
                "source_image": str(photo),
                "estimated_seconds": 2,
                "user_confirmed_slow": True,
            }
        ),
        encoding="utf-8",
    )
    clips = paths.work_audio_dir / "edge_clips"
    clips.mkdir(parents=True)
    (clips / "clip_001.wav").write_bytes(b"x")
    (clips / "clip_002.wav").write_bytes(b"x")

    cfg = {
        "sadtalker_root": str(tmp_path / "sadtalker"),
        "sadtalker": {"still": True, "preprocess": "full", "face_model_resolution": 512},
        "has_cuda": False,
    }

    with patch("build_avatar.run_sadtalker_segment") as mock_seg, patch(
        "build_avatar.concat_avatar_clips"
    ) as mock_cat:
        def _fake_seg(**kwargs):
            kwargs["out_mp4"].parent.mkdir(parents=True, exist_ok=True)
            kwargs["out_mp4"].write_bytes(b"mp4")

        mock_seg.side_effect = _fake_seg
        mock_cat.side_effect = lambda clip_mp4s, gap_seconds, output: output.write_bytes(b"out")
        out = build_avatar(paths, presenter_cfg=cfg)

    assert mock_seg.call_count == 2
    assert out == paths.avatar_mp4
    report = json.loads(paths.avatar_report_json.read_text(encoding="utf-8"))
    assert len(report["segments"]) == 2
    assert all(s["status"] == "ok" for s in report["segments"])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_build_avatar.py -v`  
Expected: FAIL

- [ ] **Step 3: 实现 `build_avatar.py`**

要点：
- 默认 gap 与 `build_narration.DEFAULT_GAP` 一致（`0.45`）；可从 segments 推算段间间隔，v1 固定 `0.45` 即可
- `run_sadtalker_segment` 用 `subprocess.run(..., check=True)`；`--cpu` 当 `has_cuda=False` 时加上
- Python 解释器：`Path(sadtalker_root) / "venv" / "bin" / "python"`（install 脚本约定）
- CLI：`--output-dir` 必填

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_build_avatar.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skill/scripts/build_avatar.py tests/test_build_avatar.py
git commit -m "$(cat <<'EOF'
feat: 增加 build_avatar 分段调用本地 SadTalker

EOF
)"
```

---

### Task 4: install_presenter.sh + doctor 可选报告

**Files:**
- Create: `scripts/install_presenter.sh`
- Modify: `skill/scripts/doctor.py`
- Test: `tests/test_doctor.py`（追加 presenter 可选键）

**Interfaces:**
- `install_presenter.sh`：
  - 环境变量 / 参数：`SADTALKER_ROOT` 默认 `$HOME/.sadtalker`；`--force` 重装
  - 步骤：`git clone` OpenTalker/SadTalker（若目录不存在）→ `python3 -m venv venv` → `pip install` 按上游 `requirements.txt`（文档注明：无 CUDA 时可能需 CPU 版 torch，脚本检测 `nvidia-smi` 失败则 `export` 提示并安装 CPU 轮子或打印手工步骤）
  - 下载官方 checkpoint（按 SadTalker README 的脚本或 `wget` 列表；失败则 exit 非 0 并说明）
  - 探测 CUDA：`nvidia-smi` 成功则 `has_cuda=true`
  - 写 `~/.screencast-explainer/presenter.json`：`enabled=true`，`installed=true`，`sadtalker_root`，`has_cuda`
  - **不**收集半身照；打印「半身照将在首次成片启用时收集」
- `doctor.check_dependencies()` 增加可选键（主流程 required 列表不变）：
  - `presenter_enabled` / `presenter_installed` / `presenter_has_cuda` / `presenter_avatar`  
    值：`available` / `unavailable` / `not_configured`（未装能力时用 `not_configured`，exit code 仍 0）

- [ ] **Step 1: 写 doctor 测试**

```python
def test_doctor_includes_optional_presenter_keys(monkeypatch, tmp_path):
    cfg = tmp_path / "presenter.json"
    cfg.write_text(
        '{"enabled": true, "installed": true, "has_cuda": false, "avatar_image": null}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "doctor.presenter_config_path",
        lambda: cfg,
    )
    # 若 doctor 通过 presenter_config 模块加载，则 monkeypatch load_presenter_config
    from doctor import check_dependencies

    result = check_dependencies()
    assert "presenter_installed" in result
    assert result["presenter_installed"] in {"available", "unavailable", "not_configured"}
```

实现时以实际导入路径为准；目标是**不因 presenter 缺失而 `sys.exit(1)`**。

- [ ] **Step 2: 跑测试确认失败后实现 doctor 扩展**

Run: `pytest tests/test_doctor.py -v`

- [ ] **Step 3: 实现 `scripts/install_presenter.sh`**

脚本须 `set -euo pipefail`；开头注释说明「须由 Agent 在用户确认后调用，禁止静默」；`--dry-run` 只打印。

最小克隆与 venv 骨架：

```bash
SADTALKER_ROOT="${SADTALKER_ROOT:-$HOME/.sadtalker}"
REPO_URL="https://github.com/OpenTalker/SadTalker.git"
# clone if missing; create venv; pip install -r requirements.txt
# detect cuda; write presenter.json via python3 -c 调用 lib.presenter_config
```

权重下载：跟上游 README（`bash scripts/download_models.sh` 若存在）；否则在脚本内列出官方 URL 并 `curl -L`。

- [ ] **Step 4: 本地 dry-run**

Run: `bash scripts/install_presenter.sh --dry-run`  
Expected: 打印将执行步骤，不写盘或仅写临时

- [ ] **Step 5: Commit**

```bash
git add scripts/install_presenter.sh skill/scripts/doctor.py tests/test_doctor.py
git commit -m "$(cat <<'EOF'
feat: 增加 SadTalker 安装脚本与 doctor 可选 presenter 状态

EOF
)"
```

---

### Task 5: Agent 文档与 SKILL 硬规则

**Files:**
- Create: `skill/references/presenter-avatar.md`
- Modify: `docs/install.md`、`docs/update.md`、`skill/SKILL.md`、`README.md`、`README.zh-CN.md`、`skill/references/standard-pipeline.md`

**Interfaces:** 无代码接口；Agent 必须遵守 reference 中的确认剧本。

- [ ] **Step 1: 写 `presenter-avatar.md`**

必须包含：
1. 能力说明（真人 only）
2. 安装确认剧本 + 无 CUDA 确认话术
3. 成片三步确认 + 耗时公式（与 `estimate_avatar_minutes` 一致）
4. 半身照要求与路径
5. 流水线顺序与命令示例：

```bash
python3 <skill-root>/scripts/build_avatar.py --output-dir "$RUN"
python3 <skill-root>/scripts/compose_video.py --output-dir "$RUN"
# 或 --with-avatar / --no-avatar
```

6. 硬规则列表（禁止静默等）

- [ ] **Step 2: 更新 `docs/install.md`**

在 doctor 成功后追加 **Step N: 可选 — 真人讲解画面**：
- 询问用户
- 否 → 写 `enabled=false`（调用一小段 python 或 echo JSON）
- 是 → 说明耗时表 → 检测 CUDA → 确认 → `bash ~/.screencast-explainer/scripts/install_presenter.sh`（路径以仓库为准：`$REPO/scripts/install_presenter.sh`）

- [ ] **Step 3: 更新 `SKILL.md`**

- 参考表增加 `presenter-avatar.md`
- 在 narrate 之后、录屏之前增加可选步骤与硬规则引用
- 成功标准可补一句「若启用则右下角有真人讲解」

- [ ] **Step 4: 更新 `standard-pipeline.md`、`update.md`、双语 README**

- pipeline 图增加可选 `build_avatar`
- update：如何 `git -C ~/.sadtalker pull` + 重跑 install；如何设 `enabled=false`
- README：Demo/功能区一句「可选本地 SadTalker 真人讲解画中画」

- [ ] **Step 5: Commit**

```bash
git add skill/references/presenter-avatar.md docs/install.md docs/update.md \
  skill/SKILL.md skill/references/standard-pipeline.md README.md README.zh-CN.md
git commit -m "$(cat <<'EOF'
docs: 真人讲解可选能力的安装与成片确认剧本

EOF
)"
```

---

### Task 6: 全量回归

- [ ] **Step 1: 跑全量 pytest**

Run: `pytest -v`  
Expected: 全部 PASS（含原有约 49+ 新用例）

- [ ] **Step 2: 无 presenter 时 compose 行为不变烟测**

用已有 smoke 思路或最小 fixture：无 `avatar.json` 时 `build_mux_command` 不含 avatar 输入。

- [ ] **Step 3: Commit（若有修复）**

仅在有 bugfix 时提交。

---

## Spec Coverage Checklist

| 规格要求 | Task |
|----------|------|
| 安装确认 + 无 CUDA 强警告 | 4, 5 |
| `presenter.json` / 半身照路径 | 1, 5 |
| 成片三步确认与耗时估算 | 1（公式）, 5（剧本） |
| `avatar.json` + 分段 SadTalker | 3 |
| 圆形右下角 PiP、字幕之上 | 2 |
| doctor 可选不阻断 | 4 |
| 失败可无角色继续 | 2, 5 |
| 非目标（卡通/云 API） | 文档写明，无实现任务 |

## Out of Scope（本计划不做）

- 真实机上跑通 10 分钟 SadTalker 端到端（依赖用户 GPU/权重下载；计划仅保证脚本与 mock 测试）
- 云端 fallback
- 卡通形象

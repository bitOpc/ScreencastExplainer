# Screencast Explainer — Design Spec

**Date:** 2026-07-13  
**Status:** Approved (brainstorming)  
**Target:** macOS skill project installable on Hermes, Codex, Claude Code, OpenClaw

---

## 1. Summary

Build `ScreencastExplainer` as the canonical repository for a cross-platform Agent skill that produces **real desktop app screencast explainer videos** (narration + hard-coded subtitles), not black-background subtitle-only videos.

**Architecture choice:** Skill + standalone Python scripts (方案 1).

**Key constraints (user decisions):**

| Decision | Choice |
|----------|--------|
| Code ownership | Migrate & generalize from `/Users/alan/Documents/视频处理/tools/` into this repo |
| v1 app support | Generic skeleton — no app-specific adapters |
| UI automation | Pure Computer Use — no bundled C/Swift input helpers |
| Install | `install.sh` one-click to 4 platforms, `--platform` filter |
| Output dir | `./outputs/<run-id>/`, overridable via `--output-dir` |
| Capture mode | Live **single-window** recording via `screencapture -v -l` (not full display; not frame collage) |
| Verification | No `verify_keyframes.py` — deliver video directly |
| Documentation language | 简体中文（文档与代码注释） |

### 语言约定

本仓库所有**文档**与**代码注释**统一使用**简体中文**：

| 范围 | 语言 | 说明 |
|------|------|------|
| `README.md` | 中文 | 项目说明、快速开始 |
| `skill/SKILL.md` | 中文 | Agent 工作流正文；frontmatter `description` 同为中文 |
| `skill/references/*.md` | 中文 | 参考文档 |
| `docs/` | 中文 | 设计 spec、实现计划等 |
| Python / Shell 代码注释 | 中文 | 函数说明、非显而易见逻辑 |
| CLI `--help` 与错误/提示信息 | 中文 | 面向用户的终端输出 |
| 代码标识符 | 英文 | 文件名、变量名、函数名、JSON 字段名保持英文 |

实现阶段不得混用英文文档或英文注释，除非引用外部 API / 工具原名（如 `ffmpeg`、`Edge TTS`）。

---

## 2. Repository Structure

```
ScreencastExplainer/
├── skill/                          # Self-contained; install.sh symlinks this dir
│   ├── SKILL.md
│   ├── references/
│   │   ├── standard-pipeline.md
│   │   ├── voice-presets.md
│   │   ├── failure-modes.md
│   │   ├── segment-schema.md
│   │   └── install-paths.md
│   └── scripts/
│       ├── doctor.py
│       ├── init_run.py
│       ├── build_narration.py
│       ├── ingest_capture.py
│       └── compose_video.py
├── install.sh
├── requirements.txt
├── README.md
├── docs/superpowers/specs/
└── outputs/                        # .gitignore
    └── <run-id>/
```

### Responsibility Split

| Role | Does | Does NOT |
|------|------|----------|
| **Agent (Computer Use)** | Open app, scroll/page in background; obtain `window_id` | Timeline math, ffmpeg command construction |
| **Python / record_window** | Single-window live capture via `screencapture -v -l` → `capture/raw.mp4`; narration; compose | UI click/scroll |
| **SKILL.md** | Enforce workflow 0→9, failure modes, delivery format | Executable logic |

---

## 3. Output Directory Layout

```
outputs/<run-id>/
├── run.json
├── script.md
├── segments.json
├── narration.wav
├── captions.srt
├── captions.ass
├── capture/
│   └── raw.mp4
└── video/
    ├── normalized.mp4
    └── final.mp4
```

---

## 4. Data Model: `segments.json`

Single file, updated in place through two phases.

### Phase 1 — Draft (`status: draft`)

Agent writes after scripting. 8–14 segments.

```json
{
  "version": 1,
  "status": "draft",
  "segments": [
    {
      "id": 1,
      "text": "我是艾达，今天带大家看一下……",
      "expected_duration": 12.0,
      "page_target": "文档开头 / 第一章标题",
      "scroll_action": "scroll_down",
      "ui_target": "主内容区",
      "notes": "开场停留 2 秒再滚动"
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `text` | yes | Narration text |
| `expected_duration` | yes | Agent-estimated seconds for scroll pacing |
| `page_target` | yes | Natural-language UI position for this segment |
| `scroll_action` | yes | `none` / `scroll_down` / `page_down` / `click` / `switch_tab` / etc. |
| `ui_target` | recommended | Target UI region |
| `notes` | optional | Hints for Agent during recording |

### Phase 2 — Narrated (`status: narrated`)

`build_narration.py` appends per segment:

```json
{
  "start": "00:00:00,000",
  "end": "00:00:11,800",
  "actual_duration": 11.8
}
```

Timestamps use SRT format (consistent with existing `edge_narrate.py`).

### `run.json`

Tracks run metadata: `run_id`, `created_at`, `status`, `voice_provider`, `voice_id`, `voice_rate`, `voice_style`, `target_description`.

Status progression: `initialized` → `narrated` → `ingested` → `composed`.

---

## 5. CLI Scripts

All scripts accept `--output-dir` and read/write within that directory.

### 5.1 `doctor.py`

```bash
python3 <skill-root>/scripts/doctor.py [--json]
```

Checks: `python3`, `ffmpeg`, `ffprobe`, `edge-tts` (import), CJK font (Pillow probe).

Does NOT check Computer Use or target app (Agent reports separately).

Default voice when Edge TTS available and user unspecified: `zh-CN-YunxiNeural` @ `-3%`.

### 5.2 `init_run.py`

```bash
python3 <skill-root>/scripts/init_run.py \
  --output-dir ./outputs/<run-id> \
  [--voice-id zh-CN-YunxiNeural] \
  [--voice-rate -3%]
```

Creates directory tree and initial `run.json`.

### 5.3 `build_narration.py`

```bash
python3 <skill-root>/scripts/build_narration.py \
  --output-dir ./outputs/<run-id> \
  [--voice-id zh-CN-YunxiNeural] \
  [--voice-rate -3%] \
  [--gap 0.45]
```

- Reads `segments.json` (`status: draft`)
- Edge TTS per-segment synthesis → `narration.wav`
- Writes `captions.srt`, `captions.ass`
- Updates segments with `start` / `end` / `actual_duration`
- Sets `status: narrated`

**Migrate from:** `edge_narrate.py` + `write_subtitles()` in `build_obsidian_llm_explainer.py`.

### 5.4 `ingest_capture.py`

```bash
python3 <skill-root>/scripts/ingest_capture.py \
  --output-dir ./outputs/<run-id>
```

- Reads `capture/raw.mp4` (Agent-produced live recording)
- Compares duration to `narration.wav` via `ffprobe` (tolerance ±0.5s)
- On mismatch: exit with error, prompt Agent to re-record
- Normalize/trim/pad as needed → `video/normalized.mp4`
- Sets `status: ingested`

**Migrate from:** duration validation in `record_obsidian_live_llm.py`.

No `--mode` flag. No frame-sequence support.

### 5.5 `compose_video.py`

```bash
python3 <skill-root>/scripts/compose_video.py \
  --output-dir ./outputs/<run-id> \
  [--crf 18]
```

- Inputs: `video/normalized.mp4` + `narration.wav` + `captions.ass`
- Output: `video/final.mp4` (ffmpeg `ass` filter, hard subtitles)
- Sets `status: composed`

**Migrate from:** `mux()` in `record_obsidian_live_llm.py`.

### Agent Call Sequence

```
doctor → init_run
→ [Agent writes script.md + segments.json]
→ build_narration
→ [Agent: Computer Use open app, calibrate scroll, live record → capture/raw.mp4]
→ ingest_capture → compose_video
→ deliver
```

---

## 6. SKILL.md — Multi-Platform Adaptation

### Frontmatter

```yaml
---
name: screencast-explainer
description: >
  用 Computer Use 驱动桌面 App 完成真实界面实时录屏，围绕界面内容生成
  带旁白与硬字幕的讲解视频。适用于 Obsidian、浏览器、IDE、办公软件等
  可视化应用。执行前必须做依赖检查；先写脚本再录屏；画面必须随讲解推进。
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [screencast, video, computer-use, narration, macos]
    category: media
  openclaw:
    homepage: ""  # set when repo is published to GitHub
triggers:
  - 录屏讲解
  - 讲解视频
  - screencast explainer
  - 界面讲解
  - obsidian://
  - 桌面 App 讲解
---
```

### Install Paths

| Platform | Path |
|----------|------|
| Hermes | `~/.hermes/profiles/ailearn/skills/screencast-explainer/` |
| Codex | `~/.codex/skills/screencast-explainer/` |
| Claude Code | `~/.claude/skills/screencast-explainer/` |
| OpenClaw | `~/.agents/skills/screencast-explainer/` |

### Mandatory Workflow

**Step 0 — Dependency check (non-skippable)**

```bash
python3 <skill-root>/scripts/doctor.py --json
```

Agent additionally reports: Computer Use, Target App, Screen Recording Permission.

Any unavailable → abort with explanation.

**Step 1 — Understand input**

Extract: target app/entry, intro, series intro, opening line, target duration, subtitle preference, voice.

Defaults: concise style, hard subtitles on, `zh-CN-YunxiNeural` @ `-3%`.

**Step 2 — Open target UI (Computer Use)**

Open resource, activate app, confirm title/content matches target.

**Step 3 — Write script first (no recording before script)**

Write `script.md`. Do not read UI text verbatim.

**Step 4 — Segment script**

Write `segments.json` (8–14 segments). Run `init_run.py`.

**Step 5 — Generate audio & subtitles**

Run `build_narration.py`.

**Step 6 — Calibrate scroll (Computer Use, before recording)**

Test PageDown → scroll wheel → mixed → click/tab/panel switches.

Re-check UI state after each test. Do not start full recording if UI did not advance.

**Step 7 — Single-window live recording (only capture mode)**

Use `record_window.py` (`screencapture -v -l <window_id>`) for continuous single-window video while Computer Use advances the UI in the background (`raise_window=false`).

No frame-sequence collage. No full-display `record_video` as the deliverable. On failure: fix window_id/permissions/scroll, then re-record.

**Step 8 — Compose**

```bash
ingest_capture.py → compose_video.py
```

**Step 9 — Deliver**

Report: script path, audio path, subtitle path, final video path, duration, voice used.

No automated keyframe verification.

### Failure Modes

| # | Mode | Action |
|---|------|--------|
| 1 | Video has subtitles only, no real app UI | Not deliverable — re-record |
| 2 | UI stays on first screen most of the time | Re-calibrate scroll, re-record |
| 3 | Narration on later segments, UI still on early content | Re-bind scroll to segment timeline, re-record |
| 4 | `ingest_capture.py` reports A/V duration mismatch | Re-record or trim narration, re-run ingest |

### Do NOT Migrate

- `click_at.c`, `scroll_wheel.c`, `key_press.c` (native input helpers)
- `build_obsidian_llm_explainer.py` (Pillow fake UI rendering)
- Frame-sequence offline synthesis logic
- `verify_keyframes.py`

---

## 7. `install.sh`

```bash
./install.sh [OPTIONS]

OPTIONS:
  --platform <list>       hermes,codex,claude,openclaw (default: all)
  --hermes-profile <name> default: ailearn
  --dry-run               print actions only
  --force                 remove existing non-symlink targets
  --uninstall             remove symlinks pointing to this repo's skill/
  -h, --help
```

Logic:

1. `REPO_ROOT` = directory containing `install.sh`
2. `SKILL_SRC` = `$REPO_ROOT/skill`
3. For each platform: `ln -sfn "$SKILL_SRC" "<target>"`
4. Skip if correct symlink already exists
5. Error if target exists and is not a symlink (unless `--force`)
6. Warn if not macOS (Darwin)

Post-install message includes `pip install -r requirements.txt` and `python3 skill/scripts/doctor.py`.

---

## 8. Dependencies

### Python (`requirements.txt`)

```
edge-tts>=6.1.0
Pillow>=10.0.0
```

### System

- `ffmpeg` / `ffprobe` (recommend `brew install ffmpeg`)
- Python 3.10+
- Edge TTS (via pip)
- CJK font (macOS system fonts)
- Computer Use capability (Agent-side)
- Screen Recording permission (macOS)

### Default Voice

| Field | Value |
|-------|-------|
| `voice_provider` | Edge TTS |
| `voice_id` | `zh-CN-YunxiNeural` |
| `voice_style` | 中文自然男声 |
| `voice_rate` | `-3%` |

---

## 9. Implementation Priority (v1)

| Order | Task |
|-------|------|
| 1 | Repo skeleton + `install.sh` + `README` + `.gitignore` |
| 2 | `doctor.py` + `init_run.py` |
| 3 | `build_narration.py` |
| 4 | `ingest_capture.py` + `compose_video.py` |
| 5 | `SKILL.md` + reference docs（全文中文） |
| 6 | End-to-end manual validation |

---

## 10. Architecture Diagram

```
┌─────────────┐     Computer Use      ┌──────────────┐
│   Agent     │ ──────────────────► │  Desktop App │
│ (4 platforms)│ ◄── state confirm ── │              │
└──────┬──────┘                       └──────────────┘
       │ script.md / segments.json
       │ live record → capture/raw.mp4
       ▼
┌─────────────┐
│ skill/      │
│ scripts/    │  doctor → init → narrate → ingest → compose
└─────────────┘
       │
       ▼
  video/final.mp4
```

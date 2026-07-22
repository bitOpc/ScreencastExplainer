# 标准流水线

Screencast Explainer 采用 **Computer Use 校准 + cua-driver 本地动作回放 + 单窗口录屏 + Python + ffmpeg** 架构。

## 架构图

```
┌─────────────┐   Computer Use 校准     ┌──────────────┐
│   Agent     │ ─────────────────────► │ 目标 App 窗口 │
│ (4 platforms)│                        └──────▲───────┘
└──────┬──────┘                                │
       │ script.md / segments.json / actions.json
       │ run_recording.py                      │
       │ (screencapture -v -l window_id) ──────┘
       │ (timeline_player.py → cua-driver)
       │         → capture/raw.mp4
       ▼
┌─────────────┐
│ skill/      │
│ scripts/    │  doctor → init → narrate → ingest → compose → cover
└─────────────┘
       │
       ▼
  video/final.mp4
  video/cover.png
```

## 职责划分

| 角色 | 负责 | 不负责 |
|------|------|--------|
| **Agent（Computer Use）** | 打开 App、校准 UI 动作、写 `actions.json`；获取 `window_id` | 录屏期间逐步推进 UI、ffmpeg 命令构造 |
| **`timeline_player.py`** | 按 `actions.json` 直连 cua-driver 回放 `key` / `click` / `scroll` / `drag` 等动作 | 理解 UI、决定讲解内容 |
| **`record_window.py`** | 对单个窗口做真实连续录屏 → `capture/raw.mp4` | UI 点击/滚动 |
| **其余 Python 脚本** | 依赖检查、配音、字幕、采集校验、合成 | UI 操作与窗口选取 |
| **SKILL.md** | 强制工作流 0→9、失败模式、交付格式 | 可执行逻辑 |

## 各层详细职责

### 1. Agent（Computer Use）

- 打开目标 App 并确认界面状态
- 撰写 `script.md` 与 `segments.json`
- 校准滚动/翻页/点击/键盘/拖动等 UI 动作
- 写入 `actions.json`
- 查询并固定目标 `window_id`
- 启动 `run_recording.py`，由本地脚本后台推进画面
- 目视确认成片窗口内容正确
- 向用户交付最终清单

Agent **不得**用截图拼视频，也不得用整屏录制冒充单窗口成片。

### 2. Python 脚本（`<skill-root>/scripts/`）

| 脚本 | 职责 |
|------|------|
| `doctor.py` | 检查 python3、ffmpeg、ffprobe、screencapture、edge-tts、中文字体 |
| `init_run.py` | 创建输出目录树与初始 `run.json` |
| `build_narration.py` | Edge TTS 逐段合成 → `narration.wav` + 字幕 |
| `timeline_player.py` | 按 `actions.json` 通过 cua-driver 后台回放 UI 动作 |
| `run_recording.py` | 同时运行录屏与动作时间轴 |
| `record_window.py` | `screencapture -v -l` 单窗口录屏 → `capture/raw.mp4` |
| `ingest_capture.py` | 校验录屏时长、标准化 → `video/normalized.mp4` |
| `compose_video.py` | 混合旁白 + 硬字幕 → `video/final.mp4` |

共享库位于 `skill/scripts/lib/`：

- `paths.py` — 输出目录路径解析
- `action_timeline.py` — `actions.json` 解析、校验与 cua-driver 调用映射
- `timefmt.py` — SRT/ASS 时间格式互转
- `subtitles.py` — 生成字幕文件
- `ffmpeg_util.py` — ffmpeg/ffprobe 封装
- `run_state.py` — 读写 `run.json`、`segments.json`

### 3. ffmpeg / ffprobe

- 读取音视频时长
- 标准化录屏
- 混合音频与硬字幕

## 标准调用顺序

```bash
python3 <skill-root>/scripts/doctor.py --json

python3 <skill-root>/scripts/init_run.py \
  --output-dir ./outputs/<run-id>

# Agent 写入 script.md + segments.json（draft）

python3 <skill-root>/scripts/build_narration.py \
  --output-dir ./outputs/<run-id>

# Agent 写入 actions.json 并取得 window_id 后：
python3 <skill-root>/scripts/timeline_player.py \
  --actions ./outputs/<run-id>/actions.json \
  --output-dir ./outputs/<run-id> \
  --dry-run

python3 <skill-root>/scripts/run_recording.py \
  --output-dir ./outputs/<run-id> \
  --window-id <WINDOW_ID>

python3 <skill-root>/scripts/ingest_capture.py \
  --output-dir ./outputs/<run-id>

python3 <skill-root>/scripts/compose_video.py \
  --output-dir ./outputs/<run-id>
```

更多录屏细节见 [recording-window.md](recording-window.md)，动作时间轴见 [action-timeline.md](action-timeline.md)。

## 状态流转

```
initialized → narrated → ingested → composed
```

录屏本身不改写 `run.json` 状态；`ingest_capture.py` 成功后才进入 `ingested`。

## 采集模式

**仅支持单窗口实时录屏**（`screencapture -v -l`）。

禁止：

- 连续采帧离线合成
- 截图序列拼视频
- cua-driver 整屏 `record_video` 作为正式产物
- 整屏 + crop 伪单窗口

## 为什么需要 Python

Computer Use 擅长 UI 理解与校准，但正式录屏期间如果每个动作都经过 LLM 工具层，会造成大量 token 与缓存重读。录屏交给系统 `screencapture`，动作回放交给 `timeline_player.py` 直连 cua-driver，合成交给 Python。

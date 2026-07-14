# 标准流水线

Screencast Explainer 采用 **Computer Use + 单窗口录屏 + Python + ffmpeg** 架构。

## 架构图

```
┌─────────────┐   Computer Use（后台）  ┌──────────────┐
│   Agent     │ ─────────────────────► │ 目标 App 窗口 │
│ (4 platforms)│                        └──────▲───────┘
└──────┬──────┘                                │
       │ script.md / segments.json             │
       │ record_window.py                      │
       │ (screencapture -v -l window_id) ──────┘
       │         → capture/raw.mp4
       ▼
┌─────────────┐
│ skill/      │
│ scripts/    │  doctor → init → narrate → ingest → compose
└─────────────┘
       │
       ▼
  video/final.mp4
```

## 职责划分

| 角色 | 负责 | 不负责 |
|------|------|--------|
| **Agent（Computer Use）** | 打开 App、校准滚动、按时间轴后台操作 UI；获取 `window_id` | 时间轴计算、ffmpeg 命令构造 |
| **`record_window.py`** | 对单个窗口做真实连续录屏 → `capture/raw.mp4` | UI 点击/滚动 |
| **其余 Python 脚本** | 依赖检查、配音、字幕、采集校验、合成 | UI 操作与窗口选取 |
| **SKILL.md** | 强制工作流 0→9、失败模式、交付格式 | 可执行逻辑 |

## 各层详细职责

### 1. Agent（Computer Use）

- 打开目标 App 并确认界面状态
- 撰写 `script.md` 与 `segments.json`
- 校准滚动/翻页策略
- 查询并固定目标 `window_id`
- 启动 `record_window.py` 的同时，后台推进画面（`raise_window=false`）
- 目视确认成片窗口内容正确
- 向用户交付最终清单

Agent **不得**用截图拼视频，也不得用整屏录制冒充单窗口成片。

### 2. Python 脚本（`<skill-root>/scripts/`）

| 脚本 | 职责 |
|------|------|
| `doctor.py` | 检查 python3、ffmpeg、ffprobe、screencapture、edge-tts、中文字体 |
| `init_run.py` | 创建输出目录树与初始 `run.json` |
| `build_narration.py` | Edge TTS 逐段合成 → `narration.wav` + 字幕 |
| `record_window.py` | `screencapture -v -l` 单窗口录屏 → `capture/raw.mp4` |
| `ingest_capture.py` | 校验录屏时长、标准化 → `video/normalized.mp4` |
| `compose_video.py` | 混合旁白 + 硬字幕 → `video/final.mp4` |

共享库位于 `skill/scripts/lib/`：

- `paths.py` — 输出目录路径解析
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

# Agent 取得 window_id 后：
python3 <skill-root>/scripts/record_window.py \
  --output-dir ./outputs/<run-id> \
  --window-id <WINDOW_ID>
# 与上一步并行：Computer Use 按时间轴滚动

python3 <skill-root>/scripts/ingest_capture.py \
  --output-dir ./outputs/<run-id>

python3 <skill-root>/scripts/compose_video.py \
  --output-dir ./outputs/<run-id>
```

更多录屏细节见 [recording-window.md](recording-window.md)。

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

Computer Use 擅长 UI 操作，但不适合承担旁白时间轴、字幕、时长校验与 ffmpeg 合成。录屏交给系统 `screencapture` 封装脚本，合成交给 Python。

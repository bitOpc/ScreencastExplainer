# 标准流水线

Screencast Explainer 采用 **Computer Use + Python + ffmpeg** 三段式架构，各层职责明确分离。

## 架构图

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

## 职责划分

| 角色 | 负责 | 不负责 |
|------|------|--------|
| **Agent（Computer Use）** | 打开 App、滚动/翻页、实时录屏 → `capture/raw.mp4` | 时间轴计算、ffmpeg 命令构造 |
| **Python 脚本** | 依赖检查、配音、字幕、采集校验、合成 | 任何 UI 点击/滚动 |
| **SKILL.md** | 强制工作流 0→9、失败模式、交付格式 | 可执行逻辑 |

## 各层详细职责

### 1. Agent（Computer Use）

Agent 是唯一能与桌面 UI 交互的层：

- 打开目标 App 并确认界面状态
- 撰写 `script.md` 与 `segments.json`
- 校准滚动/翻页策略（PageDown、滚轮、点击、切标签等）
- **实时录屏**，输出 `capture/raw.mp4`
- 目视确认画面随讲解推进
- 向用户交付最终清单

Agent **不得**自行构造 ffmpeg 命令或手动编辑字幕时间轴；这些由 Python 脚本完成。

### 2. Python 脚本（`<skill-root>/scripts/`）

| 脚本 | 职责 |
|------|------|
| `doctor.py` | 检查 python3、ffmpeg、ffprobe、edge-tts、中文字体 |
| `init_run.py` | 创建输出目录树与初始 `run.json` |
| `build_narration.py` | Edge TTS 逐段合成 → `narration.wav` + 字幕 + 更新 `segments.json` |
| `ingest_capture.py` | 校验录屏时长、标准化 → `video/normalized.mp4` |
| `compose_video.py` | 混合旁白 + 硬字幕 → `video/final.mp4` |

共享库位于 `skill/scripts/lib/`：

- `paths.py` — 输出目录路径解析
- `timefmt.py` — SRT/ASS 时间格式互转
- `subtitles.py` — 生成 `captions.srt` / `captions.ass`
- `ffmpeg_util.py` — ffmpeg/ffprobe 调用封装
- `run_state.py` — 读写 `run.json`、`segments.json`

### 3. ffmpeg / ffprobe

- 读取音视频时长（`ffprobe`）
- 标准化录屏（裁剪/填充/转码）
- 混合音频与硬字幕（`ass` 滤镜）
- 输出最终 `.mp4`

## 标准调用顺序

```bash
# 0. 依赖检查
python3 <skill-root>/scripts/doctor.py --json

# 1. 初始化运行目录
python3 <skill-root>/scripts/init_run.py \
  --output-dir ./outputs/<run-id>

# 2. Agent 写入 script.md + segments.json（draft）

# 3. 生成旁白与字幕
python3 <skill-root>/scripts/build_narration.py \
  --output-dir ./outputs/<run-id>

# 4. Agent 实时录屏 → capture/raw.mp4

# 5. 校验并标准化录屏
python3 <skill-root>/scripts/ingest_capture.py \
  --output-dir ./outputs/<run-id>

# 6. 合成最终视频
python3 <skill-root>/scripts/compose_video.py \
  --output-dir ./outputs/<run-id>
```

## 状态流转

`run.json` 中的 `status` 字段按以下顺序推进：

```
initialized → narrated → ingested → composed
```

| 状态 | 触发脚本 | 说明 |
|------|----------|------|
| `initialized` | `init_run.py` | 目录已创建 |
| `narrated` | `build_narration.py` | 旁白与字幕已生成 |
| `ingested` | `ingest_capture.py` | 录屏已校验并标准化 |
| `composed` | `compose_video.py` | 最终视频已输出 |

## 采集模式

**仅支持实时录屏。** 不支持连续采帧离线合成，也不提供 `--mode` 切换。

实时录屏失败时，Agent 应调整滚动策略后重新录制，而非退化为其他采集方式。

## 为什么需要 Python

Computer Use 擅长 UI 操作，但不适合承担以下稳定化工作：

1. 管理讲解脚本分段与时间轴
2. 调用 Edge TTS 逐段合成旁白
3. 生成 `.srt` / `.ass` 字幕文件
4. 校验音视频时长一致性
5. 构造并执行 ffmpeg 合成命令

因此 Agent 应始终通过 `<skill-root>/scripts/` 下的 CLI 脚本完成这些步骤，而非手工操作。

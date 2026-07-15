# Screencast Explainer

[English](README.md) | **简体中文**

跨平台 Agent Skill，用于生成**真实桌面应用录屏讲解视频**（旁白 + 硬字幕），而非黑底纯字幕视频。

详细设计见 [设计规格](docs/superpowers/specs/2026-07-13-screencast-explainer-design.md)。

## 一句话安装

把下面这句话发给 Agent（将 `bitOpc` 换成你的 GitHub 用户名；需先 push 本仓库）：

```
帮我安装 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/install.md
```

Agent 会按 [docs/install.md](docs/install.md) 克隆到 `~/.screencast-explainer`、创建 venv，并**只安装到你当前使用的 Agent 平台**（不会默认装四路）。更新 skill 见 [docs/update.md](docs/update.md)。

## 支持平台

| 平台 | 安装路径 |
|------|----------|
| Hermes | `~/.hermes/profiles/ailearn/skills/screencast-explainer/` |
| Codex | `~/.codex/skills/screencast-explainer/` |
| Claude Code | `~/.claude/skills/screencast-explainer/` |
| OpenClaw | `~/.agents/skills/screencast-explainer/` |

## 快速开始

### 1. 克隆与依赖

```bash
git clone https://github.com/bitOpc/ScreencastExplainer.git
cd ScreencastExplainer

# Python 依赖（运行时）
pip install -r requirements.txt

# 开发依赖（含 pytest，可选）
pip install -r requirements-dev.txt
```

### 2. 系统依赖

```bash
# macOS 推荐
brew install ffmpeg
```

还需：Python 3.10+、macOS `screencapture`（系统自带）、屏幕录制权限（授予运行 Agent/终端的宿主）、Agent 侧 Computer Use。

### 3. 安装 Skill

```bash
./install.sh                  # 安装到全部平台
./install.sh --platform codex # 或仅安装到指定平台
./install.sh --dry-run        # 预览安装操作
```

### 4. 验证环境

```bash
python3 skill/scripts/doctor.py
python3 skill/scripts/doctor.py --json
```

### 5. 端到端工作流（Agent 执行）

| 步骤 | 执行者 | 动作 |
|------|--------|------|
| 0 | Agent + 脚本 | `doctor.py` 依赖检查 |
| 1 | Agent | 理解用户输入（目标 App、时长、声音等） |
| 2 | Agent | Computer Use 打开目标界面 |
| 3 | Agent | 撰写 `script.md` |
| 4 | Agent + 脚本 | 写入 `segments.json`，运行 `init_run.py` |
| 5 | 脚本 | `build_narration.py` 生成旁白与字幕 |
| 6 | Agent | Computer Use 校准 UI 动作，写入 `actions.json` |
| 7 | 脚本 | `run_recording.py` 单窗口录屏 + cua-driver 本地时间轴回放 |
| 8 | 脚本 | `ingest_capture.py` → `compose_video.py` |
| 9 | Agent | 交付成片、音频、字幕路径与时长 |

```bash
RUN=outputs/my-run-$(date +%Y%m%d-%H%M%S)

python3 skill/scripts/doctor.py --json
python3 skill/scripts/init_run.py --output-dir "$RUN"
# Agent 写入 $RUN/script.md、$RUN/segments.json 与 $RUN/actions.json
python3 skill/scripts/build_narration.py --output-dir "$RUN"

# Agent 取得 window_id 后：
python3 skill/scripts/timeline_player.py --actions "$RUN/actions.json" --output-dir "$RUN" --dry-run
python3 skill/scripts/run_recording.py --output-dir "$RUN" --window-id <WINDOW_ID>

python3 skill/scripts/ingest_capture.py --output-dir "$RUN"
python3 skill/scripts/compose_video.py --output-dir "$RUN"
```

单窗口录屏细节见 `skill/references/recording-window.md`，通用动作时间轴见 `skill/references/action-timeline.md`。
最终成片：`$RUN/video/final.mp4`

## 目录结构

```
ScreencastExplainer/
├── skill/                      # Skill 主体（install.sh 会创建符号链接）
│   ├── SKILL.md                # Agent 强制工作流（中文）
│   ├── references/             # 参考文档（中文）
│   │   ├── standard-pipeline.md
│   │   ├── voice-presets.md
│   │   ├── failure-modes.md
│   │   ├── segment-schema.md
│   │   ├── action-timeline.md
│   │   └── install-paths.md
│   └── scripts/
│       ├── doctor.py
│       ├── init_run.py
│       ├── build_narration.py
│       ├── timeline_player.py
│       ├── run_recording.py
│       ├── ingest_capture.py
│       └── compose_video.py
├── install.sh
├── requirements.txt
├── requirements-dev.txt
├── tests/
├── docs/
└── outputs/                    # 运行输出（已 gitignore）
    └── <run-id>/
        ├── run.json
        ├── script.md
        ├── segments.json
        ├── actions.json
        ├── actions.report.json
        ├── narration.wav
        ├── captions.srt
        ├── captions.ass
        ├── capture/raw.mp4
        └── video/final.mp4
```

## 文档

| 文档 | 说明 |
|------|------|
| [skill/SKILL.md](skill/SKILL.md) | Agent 强制工作流（步骤 0–9） |
| [skill/references/standard-pipeline.md](skill/references/standard-pipeline.md) | Computer Use + Python + ffmpeg 架构 |
| [skill/references/voice-presets.md](skill/references/voice-presets.md) | 默认声音与可配置字段 |
| [skill/references/failure-modes.md](skill/references/failure-modes.md) | 四类常见失败模式 |
| [skill/references/segment-schema.md](skill/references/segment-schema.md) | `segments.json` 数据模型 |
| [skill/references/action-timeline.md](skill/references/action-timeline.md) | `actions.json` 通用 UI 动作时间轴 |
| [skill/references/install-paths.md](skill/references/install-paths.md) | 四平台安装路径 |
| [skill/references/computer-use-token-policy.md](skill/references/computer-use-token-policy.md) | 省 token 策略（Agent 指引，非代码模式） |
| [docs/install.md](docs/install.md) | Agent 一句话安装剧本 |
| [docs/update.md](docs/update.md) | Agent 更新剧本 |
| [设计规格](docs/superpowers/specs/2026-07-13-screencast-explainer-design.md) | 完整设计文档 |

## 测试

```bash
pip install -r requirements-dev.txt
pytest
```

## 冒烟验证

在不依赖真实桌面录屏的情况下，可用占位视频跑通完整 Python 流水线，验证旁白、字幕与合成步骤。

**前置条件：** 已安装 Python 依赖（`requirements.txt`）、ffmpeg，且 `doctor.py` 全部检查通过。`build_narration.py` 需联网调用 Edge TTS。

```bash
source .venv/bin/activate   # 如使用虚拟环境
RUN=outputs/smoke-$(date +%Y%m%d-%H%M%S)

python3 skill/scripts/doctor.py
python3 skill/scripts/init_run.py --output-dir "$RUN"

# 写入 script.md 与 segments.json（draft，2 段中文旁白即可）
# 示例 segments.json 见 skill/references/segment-schema.md

python3 skill/scripts/build_narration.py --output-dir "$RUN"

# 用黑屏占位视频替代真实录屏，时长与 narration.wav 对齐
AUDIO_DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$RUN/narration.wav")
ffmpeg -y -f lavfi -i color=c=black:s=1920x1080:d=$AUDIO_DUR -pix_fmt yuv420p "$RUN/capture/raw.mp4"

python3 skill/scripts/ingest_capture.py --output-dir "$RUN"
python3 skill/scripts/compose_video.py --output-dir "$RUN"
```

**预期结果：**

- `$RUN/narration.wav`、`captions.srt`、`captions.ass` 已生成
- `segments.json` 状态为 `narrated`
- `$RUN/video/final.mp4` 存在且可播放（含硬字幕与旁白）

**全量单元测试：**

```bash
pytest -v
```

Expected: 32 passed

## 卸载

```bash
./install.sh --uninstall
```

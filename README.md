# Screencast Explainer

跨平台 Agent Skill，用于生成**真实桌面应用录屏讲解视频**（旁白 + 硬字幕），而非黑底纯字幕视频。

详细设计见 [设计规格](docs/superpowers/specs/2026-07-13-screencast-explainer-design.md)。

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
git clone <repo-url> ScreencastExplainer
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

还需：Python 3.10+、macOS 屏幕录制权限、Agent 侧 Computer Use 能力。

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
| 6 | Agent | Computer Use 校准滚动/翻页策略 |
| 7 | Agent | 实时录屏 → `capture/raw.mp4` |
| 8 | 脚本 | `ingest_capture.py` → `compose_video.py` |
| 9 | Agent | 交付成片、音频、字幕路径与时长 |

```bash
RUN=outputs/my-run-$(date +%Y%m%d-%H%M%S)

python3 skill/scripts/doctor.py --json
python3 skill/scripts/init_run.py --output-dir "$RUN"
# Agent 写入 $RUN/script.md 与 $RUN/segments.json
python3 skill/scripts/build_narration.py --output-dir "$RUN"
# Agent 实时录屏 → $RUN/capture/raw.mp4
python3 skill/scripts/ingest_capture.py --output-dir "$RUN"
python3 skill/scripts/compose_video.py --output-dir "$RUN"
```

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
│   │   └── install-paths.md
│   └── scripts/
│       ├── doctor.py
│       ├── init_run.py
│       ├── build_narration.py
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
| [skill/references/install-paths.md](skill/references/install-paths.md) | 四平台安装路径 |
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

Expected: 16 passed

## 卸载

```bash
./install.sh --uninstall
```

# Screencast Explainer — 安装指南

## 给用户

复制下面这句话发给你的 AI Agent（把 `bitOpc` 换成你的 GitHub 用户名或组织名）：

```
帮我安装 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/install.md
```

> 仓库尚未 push 到 GitHub 时，可先把本文件路径发给 Agent：
> `file:///path/to/ScreencastExplainer/docs/install.md`
> 或让 Agent 在你已 clone 的本地目录里按下方「For AI Agents」步骤执行。

> 安全模式（不自动装系统包，只检查并提示）：
> ```
> 帮我安装 Screencast Explainer（安全模式）：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/install.md
> 安装时使用 --safe
> ```

---

## For AI Agents

### Goal

安装 **Screencast Explainer** skill 及 Python 依赖，使 Agent 能按 `skill/SKILL.md` 生成「真实桌面 App 录屏 + 旁白 + 硬字幕」讲解视频。

本 skill **仅支持 macOS**。

### Boundaries

- **不要**在用户的项目 workspace 里 clone 本仓库（会污染工作区）
- **不要**使用 `sudo`，除非用户明确同意
- **不要**安装本指南未列出的系统包（`--safe` 模式下只检查、不自动安装）
- 需要用户手动授权时（屏幕录制、辅助功能等），**说明步骤并让用户操作**

### Directory Rules

| 用途 | 目录 | 示例 |
|------|------|------|
| 源码与 skill | `~/.screencast-explainer/` | `~/.screencast-explainer/skill/SKILL.md` |
| Python 虚拟环境 | `~/.screencast-explainer-venv/` | `~/.screencast-explainer-venv/bin/python3` |
| 运行产物 | **当前 session 工作目录**下的 `./outputs/` | `~/Documents/AiVideo/outputs/my-run-20260714/` |
| Skill 符号链接 | 各 Agent 平台目录 | 见 [install-paths.md](../skill/references/install-paths.md) |

> **重要：** `--output-dir` 始终相对于用户任务的工作目录（`pwd`），**不是** `~/.screencast-explainer/`。Skill 仓库只放脚本，不放成片。

### Step 1: 克隆仓库

```bash
git clone https://github.com/bitOpc/ScreencastExplainer.git ~/.screencast-explainer
```

若用户已在本地有副本，可跳过 clone，但 `install.sh` 必须在**仓库根目录**执行。

### Step 2: Python 依赖

```bash
python3 -m venv ~/.screencast-explainer-venv
source ~/.screencast-explainer-venv/bin/activate
pip install -r ~/.screencast-explainer/requirements.txt
```

> macOS Homebrew Python 若遇 `externally-managed-environment`，优先用上述 venv，不要用 `pip install --break-system-packages`。

### Step 3: 系统依赖

**必须：**

- macOS（`screencapture` 单窗口录屏）
- Python 3.10+
- `ffmpeg` / `ffprobe`

**非 `--safe` 模式可自动安装：**

```bash
brew install ffmpeg
```

**`--safe` 模式：** 只运行 `which ffmpeg ffprobe screencapture`，缺失则告诉用户自行 `brew install ffmpeg`。

### Step 4: 安装 Skill 到**当前** Agent 平台

**重要：Agent 驱动的安装，只允许装到用户正在使用的那个平台。禁止默认 `./install.sh` 装四路。**

#### 4a. 探测当前平台（按优先级）

| 平台 | 探测信号 |
|------|----------|
| **hermes** | 环境变量 `HERMES_HOME` 指向 `~/.hermes/profiles/<name>`；或 `HERMES_PROFILE=<name>`；或当前会话 skill 路径含 `~/.hermes/profiles/`；或用户明确在 Hermes 里发起安装 |
| **codex** | Cursor / Codex 会话；`CODEX_HOME`；skill 路径含 `~/.codex/skills/` |
| **claude** | Claude Code 会话；skill 路径含 `~/.claude/skills/` |
| **openclaw** | OpenClaw 会话；skill 路径含 `~/.agents/skills/` |

**Hermes profile 名称**（仅 `--platform hermes` 时需要）：

1. 从 `HERMES_HOME` 解析：`~/.hermes/profiles/<profile>` → `<profile>`
2. 或读取 `HERMES_PROFILE`
3. 仍不确定 → **问用户**当前 profile 名（例如 `video_engineer`），**不要**猜 `ailearn`

若平台无法唯一确定 → **问用户**，不要装全平台。

用户明确要求「装到全部平台」时，才可：

```bash
./install.sh --platform hermes,codex,claude,openclaw
```

#### 4b. 仅安装到探测到的平台

在仓库根目录执行（示例：Hermes + profile `video_engineer`）：

```bash
cd ~/.screencast-explainer
./install.sh --platform hermes --hermes-profile video_engineer
```

其他平台示例：

```bash
./install.sh --platform codex
./install.sh --platform claude
./install.sh --platform openclaw
./install.sh --platform hermes --hermes-profile ailearn --dry-run   # 预览
```

安装后 `<skill-root>` 仅为**该平台**下的 `screencast-explainer` 符号链接，指向 `~/.screencast-explainer/skill/`。

### Step 5: 依赖检查

```bash
source ~/.screencast-explainer-venv/bin/activate
python3 ~/.screencast-explainer/skill/scripts/doctor.py --json
```

期望：`ffmpeg`、`ffprobe`、`screencapture`、`edge_tts`、`cjk_font` 均为 `available`。

若某项失败，按输出修复后重跑 doctor。

### Step 6: 可选 — 真人讲解画面

主 skill 依赖检查通过后，询问用户是否需要「真人讲解画面」附加能力（本地 SadTalker 真人画中画）。完整剧本见 [presenter-avatar.md](../skill/references/presenter-avatar.md)。

**向用户说明：**

- 右下角圆形真人讲解小窗，口型跟随旁白；**仅真人半身照**，不支持卡通
- 完全可选；不装不影响录屏 + 旁白 + 硬字幕
- SadTalker 安装到 `~/.sadtalker/`，独立 venv，不进入主 skill venv
- 粗估耗时：NVIDIA CUDA 约旁白时长的 2–4 倍；无 CUDA **可能数小时**
- 半身照在首次成片启用时收集，安装时不要求上传

**用户选「不需要」** — 写入 `enabled=false`：

```bash
PYTHONPATH=~/.screencast-explainer/skill/scripts \
  python3 -c '
from lib.presenter_config import default_presenter_config, save_presenter_config
cfg = default_presenter_config()
cfg["enabled"] = False
save_presenter_config(cfg)
'
```

**用户选「需要」：**

1. 检测 CUDA：`nvidia-smi` 成功 → 有 GPU；否则无 CUDA
2. **无 CUDA 时**：单独告知「可能数小时」，须用户明确回复（如「我已知晓并接受较慢速度」）后才可继续
3. 用户确认后安装（**必须** `--yes`；可先 `--dry-run` 预览）：

```bash
cd ~/.screencast-explainer
bash scripts/install_presenter.sh --yes
# 预览：bash scripts/install_presenter.sh --dry-run --yes
```

> `install_presenter.sh` 无 `--yes` 会拒绝执行，防止 Agent 静默安装。

安装完成后提示：半身照将在首次成片启用时收集。`doctor.py` **不**把 SadTalker 当必检项。

### Step 7: Agent 侧能力（需用户确认）

向用户确认或自行探测并报告：

| 项 | 说明 |
|----|------|
| **Computer Use** | Hermes / cua-driver 等能否操作目标 App |
| **Target App** | 能否打开用户要讲解的界面 |
| **Screen Recording** | 系统设置 → 隐私与安全性 → 屏幕录制 → 勾选**运行 Agent/终端/Cursor 的应用** |

CuaDriver 若单独用于 Computer Use 截图，也需授予屏幕录制权限；与 `screencapture` 权限相互独立。

### Step 8: 告知用户安装结果

报告：

- 仓库路径：`~/.screencast-explainer`
- venv 激活：`source ~/.screencast-explainer-venv/bin/activate`
- skill 已链接到的**单个**平台与路径（不要汇报未安装的平台）
- `doctor.py --json` 结果摘要
- 触发方式：对 Agent 说「录屏讲解」「讲解视频」等（见 `skill/SKILL.md` triggers）
- 若用户安装了真人讲解能力，说明 `presenter.json` 路径与 `docs/install.md` Step 6

### Step 9: 可选冒烟测试

不录真实桌面时，可用占位视频验证 Python 流水线（见仓库 `README.md` 冒烟验证一节）。

---

## Quick Reference

| 命令 | 作用 |
|------|------|
| `./install.sh --platform <name>` | **Agent 安装必用**：仅装当前平台 |
| `./install.sh` | 手动安装：四平台全装（Agent 勿用） |
| `./install.sh --uninstall --platform <name>` | 仅卸载指定平台 |
| `python3 skill/scripts/doctor.py --json` | 检查脚本侧依赖 |
| `python3 skill/scripts/init_run.py --output-dir ./outputs/<id>` | 初始化一次运行 |
| `python3 skill/scripts/build_narration.py --output-dir ./outputs/<id>` | 生成旁白与字幕 |
| `bash ~/.screencast-explainer/scripts/install_presenter.sh --yes` | 可选：安装 SadTalker 真人讲解（须用户确认） |
| `python3 skill/scripts/record_window.py --output-dir ./outputs/<id> --window-id <ID>` | 单窗口录屏 |

完整工作流见 `skill/SKILL.md` 与 `skill/references/standard-pipeline.md`。

更新 skill：`帮我更新 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/update.md`

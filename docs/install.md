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
| 运行产物 | 用户项目下的 `./outputs/` | `./outputs/my-run-20260714/` |
| Skill 符号链接 | 各 Agent 平台目录 | 见 [install-paths.md](../skill/references/install-paths.md) |

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

### Step 4: 安装 Skill 到 Agent 平台

在仓库根目录执行：

```bash
cd ~/.screencast-explainer
./install.sh
```

按需指定平台：

```bash
./install.sh --platform hermes,codex,claude,openclaw
./install.sh --platform codex --dry-run   # 预览
./install.sh --hermes-profile ailearn      # Hermes 自定义 profile
```

安装后 `<skill-root>` 即各平台下的 `screencast-explainer` 符号链接，指向 `~/.screencast-explainer/skill/`。

### Step 5: 依赖检查

```bash
source ~/.screencast-explainer-venv/bin/activate
python3 ~/.screencast-explainer/skill/scripts/doctor.py --json
```

期望：`ffmpeg`、`ffprobe`、`screencapture`、`edge_tts`、`cjk_font` 均为 `available`。

若某项失败，按输出修复后重跑 doctor。

### Step 6: Agent 侧能力（需用户确认）

向用户确认或自行探测并报告：

| 项 | 说明 |
|----|------|
| **Computer Use** | Hermes / cua-driver 等能否操作目标 App |
| **Target App** | 能否打开用户要讲解的界面 |
| **Screen Recording** | 系统设置 → 隐私与安全性 → 屏幕录制 → 勾选**运行 Agent/终端/Cursor 的应用** |

CuaDriver 若单独用于 Computer Use 截图，也需授予屏幕录制权限；与 `screencapture` 权限相互独立。

### Step 7: 告知用户安装结果

报告：

- 仓库路径：`~/.screencast-explainer`
- venv 激活：`source ~/.screencast-explainer-venv/bin/activate`
- skill 已链接到的平台
- `doctor.py --json` 结果摘要
- 触发方式：对 Agent 说「录屏讲解」「讲解视频」等（见 `skill/SKILL.md` triggers）

### Step 8: 可选冒烟测试

不录真实桌面时，可用占位视频验证 Python 流水线（见仓库 `README.md` 冒烟验证一节）。

---

## Quick Reference

| 命令 | 作用 |
|------|------|
| `./install.sh` | 四平台 symlink 安装 skill |
| `./install.sh --uninstall` | 移除 symlink |
| `python3 skill/scripts/doctor.py --json` | 检查脚本侧依赖 |
| `python3 skill/scripts/init_run.py --output-dir ./outputs/<id>` | 初始化一次运行 |
| `python3 skill/scripts/build_narration.py --output-dir ./outputs/<id>` | 生成旁白与字幕 |
| `python3 skill/scripts/record_window.py --output-dir ./outputs/<id> --window-id <ID>` | 单窗口录屏 |

完整工作流见 `skill/SKILL.md` 与 `skill/references/standard-pipeline.md`。

更新 skill：`帮我更新 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/update.md`

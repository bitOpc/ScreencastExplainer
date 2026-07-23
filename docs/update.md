# Screencast Explainer — 更新指南

## 给用户

```
帮我更新 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/update.md
```

---

## For AI Agents

### Goal

将 `~/.screencast-explainer` 更新到最新代码，刷新 Python 依赖，并**仅**刷新当前 Agent 平台的 skill 符号链接。

### Step 1: 探测当前平台

与 [install.md](install.md) Step 4a 相同：只更新用户正在用的平台（hermes / codex / claude / openclaw）。Hermes 需带上正确的 `--hermes-profile`。

### Step 2: 拉代码并更新依赖

```bash
cd ~/.screencast-explainer
git pull

source ~/.screencast-explainer-venv/bin/activate
pip install -r requirements.txt
```

### Step 3: 仅重装当前平台链接

```bash
# 示例：Hermes profile video_engineer
./install.sh --platform hermes --hermes-profile video_engineer

python3 skill/scripts/doctor.py --json
```

**禁止**在无用户明确要求时运行无 `--platform` 的 `./install.sh`。

### Step 4: 可选 — 更新 SadTalker（真人讲解）

仅当用户曾安装过 Presenter Avatar（`~/.screencast-explainer/presenter.json` 中 `installed=true`）且需要更新 SadTalker 时：

```bash
# 拉取上游 SadTalker
git -C ~/.sadtalker pull

# 重跑安装脚本（刷新 venv 依赖与 presenter.json；须用户确认 --yes）
cd ~/.screencast-explainer
bash scripts/install_presenter.sh --yes
```

若用户要**关闭**真人讲解能力（不卸载 SadTalker 文件）：

```bash
PYTHONPATH=~/.screencast-explainer/skill/scripts \
  python3 -c '
from lib.presenter_config import load_presenter_config, save_presenter_config
cfg = load_presenter_config()
cfg["enabled"] = False
save_presenter_config(cfg)
'
```

详见 [presenter-avatar.md](../skill/references/presenter-avatar.md)。

### Notes

- 符号链接安装方式下，pull 后 skill 内容自动生效；`install.sh` 用于修复链接或切换 Hermes profile
- 若 doctor 失败，按 [install.md](install.md) Step 5–7 处理
- 用户项目内 `./outputs/` 历史运行数据不受影响

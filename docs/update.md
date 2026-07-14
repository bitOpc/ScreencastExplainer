# Screencast Explainer — 更新指南

## 给用户

```
帮我更新 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/update.md
```

---

## For AI Agents

### Goal

将 `~/.screencast-explainer` 更新到最新代码，刷新 Python 依赖与 skill 符号链接。

### Steps

```bash
cd ~/.screencast-explainer
git pull

source ~/.screencast-explainer-venv/bin/activate
pip install -r requirements.txt

./install.sh

python3 skill/scripts/doctor.py --json
```

### Notes

- 符号链接安装方式下，pull 后 skill 内容自动生效；`install.sh` 用于修复链接或切换 Hermes profile
- 若 doctor 失败，按 [install.md](install.md) Step 5–6 处理
- 用户项目内 `./outputs/` 历史运行数据不受影响

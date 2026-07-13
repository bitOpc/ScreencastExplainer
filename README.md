# Screencast Explainer

跨平台 Agent Skill，用于生成**真实桌面应用录屏讲解视频**（旁白 + 硬字幕），而非黑底纯字幕视频。

详细设计见 [设计规格](docs/superpowers/specs/2026-07-13-screencast-explainer-design.md)。

## 支持平台

- Hermes
- Codex
- Claude Code
- OpenClaw

## 快速开始

```bash
git clone <repo-url> ScreencastExplainer
cd ScreencastExplainer
pip install -r requirements-dev.txt
./install.sh
python3 skill/scripts/doctor.py
```

## 目录结构

```
ScreencastExplainer/
├── skill/                  # Skill 主体（install.sh 会创建符号链接）
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
├── install.sh
├── requirements.txt
├── requirements-dev.txt
├── tests/
├── docs/
└── outputs/                # 运行输出（已 gitignore）
```

## 卸载

```bash
./install.sh --uninstall
```

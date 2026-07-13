# 安装路径

Screencast Explainer 通过 `install.sh` 将仓库中的 `skill/` 目录以符号链接方式安装到各 Agent 平台的 skill 目录。

## 四平台安装路径

| 平台 | 安装路径 |
|------|----------|
| Hermes | `~/.hermes/profiles/ailearn/skills/screencast-explainer/` |
| Codex | `~/.codex/skills/screencast-explainer/` |
| Claude Code | `~/.claude/skills/screencast-explainer/` |
| OpenClaw | `~/.agents/skills/screencast-explainer/` |

安装后，`<skill-root>` 即上述路径（指向仓库 `skill/` 目录的符号链接）。

## install.sh 用法

在仓库根目录执行：

```bash
./install.sh [OPTIONS]
```

### 选项

| 选项 | 说明 |
|------|------|
| `--platform <list>` | 指定平台，逗号分隔：`hermes,codex,claude,openclaw`（默认全部） |
| `--hermes-profile <name>` | Hermes profile 名称，默认 `ailearn` |
| `--dry-run` | 仅打印将要执行的操作，不实际创建链接 |
| `--force` | 若目标已存在且非符号链接，先删除再创建 |
| `--uninstall` | 移除指向本仓库 `skill/` 的符号链接 |
| `-h, --help` | 显示帮助 |

### 示例

```bash
# 安装到全部平台
./install.sh

# 仅安装到 Codex
./install.sh --platform codex

# 预览安装操作
./install.sh --dry-run

# 安装到 Hermes 的自定义 profile
./install.sh --platform hermes --hermes-profile myprofile

# 卸载
./install.sh --uninstall
```

## 安装逻辑

1. `REPO_ROOT` = `install.sh` 所在目录
2. `SKILL_SRC` = `$REPO_ROOT/skill`
3. 对每个目标平台：`ln -sfn "$SKILL_SRC" "<target>"`
4. 若目标已是正确符号链接 → 跳过
5. 若目标存在且非符号链接 → 报错（除非 `--force`）
6. 非 macOS 系统会发出警告（本 skill 目标平台为 macOS）

## 安装后步骤

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 验证依赖
python3 skill/scripts/doctor.py

# 或从已安装路径验证
python3 ~/.codex/skills/screencast-explainer/scripts/doctor.py
```

## 脚本路径约定

文档与 SKILL.md 中使用 `<skill-root>` 占位符，表示已安装 skill 的根目录。实际调用示例：

```bash
# 仓库内开发时
python3 skill/scripts/doctor.py

# 安装后（以 Codex 为例）
python3 ~/.codex/skills/screencast-explainer/scripts/doctor.py
```

## 卸载

```bash
./install.sh --uninstall
```

仅移除符号链接，不影响仓库源码与 `outputs/` 中的历史运行数据。

## 注意事项

- 符号链接意味着修改仓库 `skill/` 目录会立即反映到各平台，无需重新安装
- 若移动仓库位置，需重新运行 `./install.sh` 更新链接
- Hermes 路径中的 `ailearn` 可通过 `--hermes-profile` 更改

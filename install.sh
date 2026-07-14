#!/usr/bin/env bash
# Screencast Explainer — 四平台 skill 安装/卸载脚本
set -euo pipefail

# 仓库根目录（install.sh 所在目录）
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$(cd "$REPO_ROOT/skill" && pwd)"
SKILL_MD="$SKILL_SRC/SKILL.md"

# 默认选项
PLATFORMS="hermes,codex,claude,openclaw"
HERMES_PROFILE="ailearn"
DRY_RUN=false
FORCE=false
UNINSTALL=false

# 彩色输出（非 TTY 时自动关闭）
if [[ -t 1 ]]; then
  RED=$'\033[0;31m'
  GREEN=$'\033[0;32m'
  YELLOW=$'\033[1;33m'
  NC=$'\033[0m'
else
  RED='' GREEN='' YELLOW='' NC=''
fi

info()  { printf '%s\n' "$*"; }
warn()  { printf '%s%s%s\n' "$YELLOW" "$*" "$NC"; }
error() { printf '%s%s%s\n' "$RED" "$*" "$NC" >&2; }
ok()    { printf '%s%s%s\n' "$GREEN" "$*" "$NC"; }

usage() {
  cat <<'EOF'
用法: ./install.sh [选项]

将本仓库 skill/ 目录以符号链接方式安装到 Agent 平台。

选项:
  --platform <列表>         目标平台，逗号分隔：hermes,codex,claude,openclaw
                            （默认全部；Agent 安装时必须显式指定单个平台）
  --hermes-profile <名称>   Hermes profile 名称（默认: ailearn）
  --dry-run                 仅打印将要执行的操作，不实际修改文件系统
  --force                   目标已存在且非符号链接时，强制删除后重新安装
  --uninstall               卸载：仅移除指向本仓库 skill/ 的符号链接
  -h, --help                显示此帮助

安装目标:
  Hermes:   $HOME/.hermes/profiles/<profile>/skills/screencast-explainer
  Codex:    $HOME/.codex/skills/screencast-explainer
  Claude:   $HOME/.claude/skills/screencast-explainer
  OpenClaw: $HOME/.agents/skills/screencast-explainer
EOF
}

# 解析命令行参数
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --platform)
        [[ $# -ge 2 ]] || { error "缺少 --platform 参数值"; exit 1; }
        PLATFORMS="$2"
        shift 2
        ;;
      --hermes-profile)
        [[ $# -ge 2 ]] || { error "缺少 --hermes-profile 参数值"; exit 1; }
        HERMES_PROFILE="$2"
        shift 2
        ;;
      --dry-run)
        DRY_RUN=true
        shift
        ;;
      --force)
        FORCE=true
        shift
        ;;
      --uninstall)
        UNINSTALL=true
        shift
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        error "未知选项: $1"
        usage
        exit 1
        ;;
    esac
  done
}

# 解析符号链接目标为绝对路径
resolve_symlink() {
  local path="$1"
  if [[ ! -L "$path" ]]; then
    return 1
  fi
  local target
  target="$(readlink "$path")"
  if [[ "$target" == /* ]]; then
    printf '%s\n' "$target"
  else
    (cd "$(dirname "$path")" && cd "$target" && pwd)
  fi
}

# 检查平台名是否有效
validate_platform() {
  local name="$1"
  case "$name" in
    hermes|codex|claude|openclaw) return 0 ;;
    *)
      error "未知平台: $name（可选: hermes, codex, claude, openclaw）"
      return 1
      ;;
  esac
}

# 根据平台名返回安装目标路径
platform_target() {
  local name="$1"
  case "$name" in
    hermes)   printf '%s\n' "$HOME/.hermes/profiles/${HERMES_PROFILE}/skills/screencast-explainer" ;;
    codex)    printf '%s\n' "$HOME/.codex/skills/screencast-explainer" ;;
    claude)   printf '%s\n' "$HOME/.claude/skills/screencast-explainer" ;;
    openclaw) printf '%s\n' "$HOME/.agents/skills/screencast-explainer" ;;
  esac
}

# 安装单个平台
install_platform() {
  local name="$1"
  local target
  target="$(platform_target "$name")"

  info ""
  info "[$name] 目标: $target"

  if $DRY_RUN; then
    info "  [dry-run] mkdir -p $(dirname "$target")"
    info "  [dry-run] ln -sfn \"$SKILL_SRC\" \"$target\""
    return 0
  fi

  mkdir -p "$(dirname "$target")"

  # 已是正确符号链接则跳过
  if [[ -L "$target" ]]; then
    local current
    current="$(resolve_symlink "$target")"
    if [[ "$current" == "$SKILL_SRC" ]]; then
      ok "  已安装（符号链接正确），跳过"
      return 0
    fi
  fi

  # 目标存在且非符号链接
  if [[ -e "$target" || -L "$target" ]]; then
    if [[ -L "$target" ]]; then
      # 符号链接指向其他位置，直接覆盖
      :
    elif $FORCE; then
      warn "  目标已存在且非符号链接，--force 删除: $target"
      rm -rf "$target"
    else
      error "  目标已存在且非符号链接: $target（使用 --force 强制覆盖）"
      return 1
    fi
  fi

  ln -sfn "$SKILL_SRC" "$target"
  ok "  已安装: $target -> $SKILL_SRC"
}

# 卸载单个平台（仅移除指向本仓库 skill/ 的符号链接）
uninstall_platform() {
  local name="$1"
  local target
  target="$(platform_target "$name")"

  info ""
  info "[$name] 目标: $target"

  if [[ ! -L "$target" ]]; then
    info "  无符号链接，跳过"
    return 0
  fi

  local current
  current="$(resolve_symlink "$target")"
  if [[ "$current" != "$SKILL_SRC" ]]; then
    warn "  符号链接指向其他位置 ($current)，跳过"
    return 0
  fi

  if $DRY_RUN; then
    info "  [dry-run] rm \"$target\""
    return 0
  fi

  rm "$target"
  ok "  已卸载: $target"
}

# 遍历选定平台并执行操作
run_for_platforms() {
  local action="$1"  # install 或 uninstall
  local failed=0
  local IFS=','

  for name in $PLATFORMS; do
    # 去除首尾空白
    name="${name#"${name%%[![:space:]]*}"}"
    name="${name%"${name##*[![:space:]]}"}"
    [[ -n "$name" ]] || continue

    validate_platform "$name" || { failed=1; continue; }

    if [[ "$action" == "install" ]]; then
      install_platform "$name" || failed=1
    else
      uninstall_platform "$name" || failed=1
    fi
  done

  return "$failed"
}

# 安装前检查
preflight() {
  if [[ ! -d "$SKILL_SRC" ]]; then
    error "skill 目录不存在: $SKILL_SRC"
    exit 1
  fi

  if [[ ! -f "$SKILL_MD" ]]; then
    error "缺少 skill/SKILL.md，请先完成 skill 文档后再安装"
    exit 1
  fi

  if [[ "$(uname -s)" != "Darwin" ]]; then
    warn "警告: 本 skill 面向 macOS 设计，当前系统可能无法完整运行"
  fi
}

# 安装完成提示
post_install_message() {
  info ""
  ok "安装完成！后续步骤："
  info "  pip install -r requirements.txt"
  info "  python3 skill/scripts/doctor.py"
}

main() {
  parse_args "$@"

  if $UNINSTALL; then
    info "卸载 Screencast Explainer skill（平台: $PLATFORMS）"
    run_for_platforms uninstall || exit 1
    ok "卸载完成"
    exit 0
  fi

  preflight

  info "安装 Screencast Explainer skill"
  info "  源目录: $SKILL_SRC"
  info "  平台:   $PLATFORMS"
  if [[ "$PLATFORMS" == *"hermes"* ]]; then
    info "  Hermes profile: $HERMES_PROFILE"
  fi
  if $DRY_RUN; then
    warn "（dry-run 模式，不会实际修改文件系统）"
  fi

  run_for_platforms install || exit 1

  if ! $DRY_RUN; then
    post_install_message
  fi
}

main "$@"

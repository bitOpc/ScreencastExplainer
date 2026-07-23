#!/usr/bin/env bash
# 必须由 Agent 在获得用户明确确认后调用；禁止默认或静默安装 SadTalker。

set -euo pipefail

SADTALKER_ROOT="${SADTALKER_ROOT:-$HOME/.sadtalker}"
REPO_URL="https://github.com/OpenTalker/SadTalker.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRY_RUN=false
FORCE=false
CONFIRMED=false

usage() {
  cat <<'EOF'
用法：bash scripts/install_presenter.sh [--dry-run] [--force] --yes

请仅在 Agent 已获得用户对安装（无 CUDA 时还包括较慢速度）的明确确认后运行。
  --dry-run  仅显示将执行的操作，不写入磁盘
  --force    删除现有 SadTalker 目录后重新安装
  --yes      表示已经获得用户明确确认
EOF
}

run() {
  if "$DRY_RUN"; then
    printf '+'
    printf ' %q' "$@"
    printf '\n'
    return
  fi
  "$@"
}

run_in_sadtalker_root() {
  if "$DRY_RUN"; then
    printf '+ (cd %q &&' "$SADTALKER_ROOT"
    printf ' %q' "$@"
    printf ' )\n'
    return
  fi
  (
    cd "$SADTALKER_ROOT"
    "$@"
  )
}

while (($#)); do
  case "$1" in
    --dry-run) DRY_RUN=true ;;
    --force) FORCE=true ;;
    --yes) CONFIRMED=true ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

if [[ "$SADTALKER_ROOT" == "/" ]]; then
  echo "SADTALKER_ROOT 不能是根目录。" >&2
  exit 2
fi

if ! "$DRY_RUN" && ! "$CONFIRMED"; then
  echo "拒绝静默安装：请先获得用户明确确认，再以 --yes 重试。" >&2
  exit 2
fi

echo "SadTalker 将安装到：$SADTALKER_ROOT"
if "$DRY_RUN"; then
  echo "Dry run：不会克隆、安装依赖、下载权重或写 presenter.json。"
fi

if "$FORCE"; then
  if [[ -e "$SADTALKER_ROOT" ]]; then
    echo "将删除已有目录后重新安装：$SADTALKER_ROOT"
    run rm -rf "$SADTALKER_ROOT"
  fi
elif [[ -e "$SADTALKER_ROOT" && ! -d "$SADTALKER_ROOT/.git" ]]; then
  echo "SADTALKER_ROOT 已存在但不是 Git 仓库；请改用空目录或传 --force。" >&2
  exit 1
fi

if [[ ! -d "$SADTALKER_ROOT" || "$FORCE" == true ]]; then
  run mkdir -p "$(dirname "$SADTALKER_ROOT")"
  run git clone "$REPO_URL" "$SADTALKER_ROOT"
else
  echo "复用现有 SadTalker 仓库。"
fi

VENV_DIR="$SADTALKER_ROOT/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
run python3 -m venv "$VENV_DIR"
run "$VENV_PYTHON" -m pip install --upgrade pip
run "$VENV_PYTHON" -m pip install -r "$SADTALKER_ROOT/requirements.txt"

has_cuda=false
if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then
  has_cuda=true
  echo "检测到 NVIDIA CUDA。"
else
  echo "未检测到 NVIDIA CUDA：将安装 PyTorch CPU 轮子；生成 avatar 可能需要数小时。"
  run "$VENV_PYTHON" -m pip install --upgrade torch torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cpu
fi

if "$DRY_RUN" || [[ -f "$SADTALKER_ROOT/scripts/download_models.sh" ]]; then
  run_in_sadtalker_root bash scripts/download_models.sh
else
  echo "未找到上游 scripts/download_models.sh，改用以下官方回退 URL 下载权重。"
  checkpoint_urls=(
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00109-model.pth.tar"
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/mapping_00229-model.pth.tar"
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_256.safetensors"
    "https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc/SadTalker_V0.0.2_512.safetensors"
  )
  run mkdir -p "$SADTALKER_ROOT/checkpoints"
  for url in "${checkpoint_urls[@]}"; do
    run curl -fL --retry 3 -o "$SADTALKER_ROOT/checkpoints/${url##*/}" "$url"
  done
fi

if "$DRY_RUN"; then
  echo "+ PYTHONPATH=$SCRIPT_DIR/../skill/scripts python3 -c '<write presenter.json via lib.presenter_config>'"
else
  SADTALKER_ROOT="$SADTALKER_ROOT" HAS_CUDA="$has_cuda" \
    PYTHONPATH="$SCRIPT_DIR/../skill/scripts${PYTHONPATH:+:$PYTHONPATH}" \
    python3 -c '
from os import environ
from lib.presenter_config import load_presenter_config, save_presenter_config

config = load_presenter_config()
config.update(
    enabled=True,
    installed=True,
    sadtalker_root=environ["SADTALKER_ROOT"],
    has_cuda=environ["HAS_CUDA"].lower() == "true",
)
save_presenter_config(config)
'
fi

echo "SadTalker 安装完成。半身照将在首次成片启用时收集。"

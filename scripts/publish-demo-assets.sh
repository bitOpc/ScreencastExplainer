#!/usr/bin/env bash
# 将 docs/assets/demo-preview.mp4 发布到 GitHub Release，供 README <video> 嵌入。
# GitHub 会剥离相对路径的 video 标签；必须使用 releases/download 或 user-attachments URL。
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-bitOpc/ScreencastExplainer}"
TAG="demo-assets"
ASSET="docs/assets/demo-preview.mp4"

if ! command -v gh >/dev/null 2>&1; then
  echo "需要 GitHub CLI: brew install gh && gh auth login" >&2
  exit 1
fi

if [[ ! -f "$ASSET" ]]; then
  echo "未找到 $ASSET，请先生成预览视频。" >&2
  exit 1
fi

if ! gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
  gh release create "$TAG" \
    --repo "$REPO" \
    --title "Demo assets" \
    --notes "README 内嵌演示视频（demo-preview.mp4）。由 scripts/publish-demo-assets.sh 维护。"
fi

gh release upload "$TAG" "$ASSET" --repo "$REPO" --clobber

echo "已上传: https://github.com/$REPO/releases/download/$TAG/demo-preview.mp4"

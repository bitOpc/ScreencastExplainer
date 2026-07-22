# Demo assets

| 文件 | 用途 |
|------|------|
| `demo-preview.mp4` | README 演示片段源文件（24s，含字幕/旁白/滚动） |

## README 视频为何不能写相对路径？

GitHub README 的安全过滤器会**移除** `<video src="docs/assets/...">` 这类相对路径标签。  
必须使用以下之一：

1. **GitHub Release 资源**（本仓库推荐）  
   `https://github.com/bitOpc/ScreencastExplainer/releases/download/demo-assets/demo-preview.mp4`

2. **user-attachments CDN**  
   在 GitHub 网页编辑器里把 mp4 拖进 README，使用生成的 `github.com/user-attachments/assets/...` URL。

## 发布 / 更新演示视频

在仓库根目录执行（需 `gh auth login`）：

```bash
chmod +x scripts/publish-demo-assets.sh
./scripts/publish-demo-assets.sh
```

封面图由 `skill/scripts/build_cover.py` 在每次成片后生成，**不**放入本目录或 README。

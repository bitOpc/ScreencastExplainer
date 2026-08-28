# 封面文案（Agent 负责）

`build_cover.py` **不**用规则/硬编码生成标题与副标题钩子。跑 Skill 的 LLM Agent 必须先根据本片内容写出 `$RUN/cover.json`，再调用渲染脚本。

## 何时写

在 `compose_video.py` 成功之后、`build_cover.py` **之前**。

## 输入

阅读：

- `script.md`
- `segments.json`（旁白与画面要点）
- 可选：成片主题 / 用户本片目标

## 输出：`$RUN/cover.json`

```json
{
  "title": "Prompt Engineering",
  "subtitle": "Prompt 是越长越好吗？",
  "frame_seconds": 8
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `title` | 是 | 主标题，通常为英文主题名（短、可上封面），如 `Attention`、`Prompt Engineering` |
| `subtitle` | 是 | 中文**钩子话术**：能引起点击/讨论，不是「文档末尾」「第 15 节」这类位置描述 |
| `frame_seconds` | 否 | 取帧秒数；省略则脚本用开场或「切换笔记」点机械推断 |
| `title_font` | 否 | 主标题字体文件路径；省略用系统默认 |
| `subtitle_font` | 否 | 副标题字体路径；省略用系统默认 |
| `subtitle_font_index` | 否 | `.ttc` 字重索引，默认 `0` |

## 文案要求（给 Agent）

1. **先总结本片真正讲什么**，再写标题；不要抓旁白里顺带提到的次要词（例如全文讲 Prompt Engineering，却用末尾出现的 `RAG` 当标题）。
2. **副标题是钩子**，优先：
   - 反常识提问：`Prompt 是越长越好吗？`
   - 短断言：`不是写漂亮提示词`、`机制深度解析`
   - 常见误解：`误解：只是写提示词？`
3. 副标题宜短（建议 ≤16 字），适合大字上封面。
4. **禁止**把 `page_target` 原文（「文档末尾 — 第 15 节」）直接当副标题。

## 渲染命令

```bash
python3 <skill-root>/scripts/build_cover.py --output-dir "$RUN"
```

临时覆盖可用 CLI（仍建议把定稿写回 `cover.json`）：

```bash
python3 <skill-root>/scripts/build_cover.py \
  --output-dir "$RUN" \
  --title "Prompt Engineering" \
  --subtitle "Prompt 是越长越好吗？" \
  --frame-seconds 8
```

缺少 `title`/`subtitle`（既无 cover.json 也无 CLI）时，脚本会报错退出，而不是瞎编钩子。

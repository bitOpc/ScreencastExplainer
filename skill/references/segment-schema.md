# segments.json 数据模型

`segments.json` 是讲解脚本的分段与时间轴核心文件，在 `./outputs/<run-id>/` 目录下维护，经历 **draft → narrated** 两个阶段。

## 顶层结构

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | `number` |  schema 版本，当前为 `1` |
| `status` | `string` | `draft` 或 `narrated` |
| `segments` | `array` | 分段数组，8–14 段 |

## 阶段 1：draft

Agent 在步骤 4 写入。此时每段包含脚本与 UI 推进计划，尚无精确时间戳。

### 段字段（draft）

| 字段 | 必填 | 类型 | 说明 |
|------|------|------|------|
| `id` | 是 | `number` | 段序号，从 1 开始 |
| `text` | 是 | `string` | 旁白文本 |
| `expected_duration` | 是 | `number` | Agent 预估时长（秒），用于录屏节奏 |
| `page_target` | 是 | `string` | 该段应对应的 UI 位置（自然语言描述） |
| `scroll_action` | 是 | `string` | 推进动作，见下表 |
| `ui_target` | 推荐 | `string` | 目标 UI 区域 |
| `notes` | 否 | `string` | 录屏时的操作提示 |

### scroll_action 取值

| 值 | 含义 |
|----|------|
| `none` | 不滚动，停留当前位置 |
| `scroll_down` | 滚轮向下 |
| `page_down` | PageDown 翻页 |
| `click` | 点击特定元素 |
| `switch_tab` | 切换标签/页签 |
| 其他 | 可扩展，如 `switch_panel`、`switch_view` 等 |

### draft 示例

```json
{
  "version": 1,
  "status": "draft",
  "segments": [
    {
      "id": 1,
      "text": "我是艾达，今天带大家看一下……",
      "expected_duration": 12.0,
      "page_target": "文档开头 / 第一章标题",
      "scroll_action": "none",
      "ui_target": "主内容区",
      "notes": "开场停留 2 秒再滚动"
    },
    {
      "id": 2,
      "text": "首先我们来了解一下整体结构……",
      "expected_duration": 15.0,
      "page_target": "第一章正文上半部分",
      "scroll_action": "scroll_down",
      "ui_target": "主内容区",
      "notes": "缓慢滚轮，配合旁白节奏"
    }
  ]
}
```

## 阶段 2：narrated

`build_narration.py` 读取 `status: draft` 的 `segments.json`，逐段调用 Edge TTS 合成旁白，并在每段追加时间戳字段。

### 追加字段（narrated）

| 字段 | 类型 | 说明 |
|------|------|------|
| `start` | `string` | 段起始时间，SRT 格式 `HH:MM:SS,mmm` |
| `end` | `string` | 段结束时间，SRT 格式 |
| `actual_duration` | `number` | 实际时长（秒） |

执行成功后，顶层 `status` 更新为 `narrated`。

### narrated 示例

```json
{
  "version": 1,
  "status": "narrated",
  "segments": [
    {
      "id": 1,
      "text": "我是艾达，今天带大家看一下……",
      "expected_duration": 12.0,
      "page_target": "文档开头 / 第一章标题",
      "scroll_action": "none",
      "ui_target": "主内容区",
      "notes": "开场停留 2 秒再滚动",
      "start": "00:00:00,000",
      "end": "00:00:11,800",
      "actual_duration": 11.8
    },
    {
      "id": 2,
      "text": "首先我们来了解一下整体结构……",
      "expected_duration": 15.0,
      "page_target": "第一章正文上半部分",
      "scroll_action": "scroll_down",
      "ui_target": "主内容区",
      "notes": "缓慢滚轮，配合旁白节奏",
      "start": "00:00:12,250",
      "end": "00:00:27,100",
      "actual_duration": 14.85
    }
  ]
}
```

## 关联产物

`build_narration.py` 同时生成：

| 文件 | 来源 |
|------|------|
| `narration.wav` | 各段 TTS 音频拼接（含段间 gap） |
| `captions.srt` | 由 `start`/`end`/`text` 生成 |
| `captions.ass` | 同上，ASS 格式供 ffmpeg 硬字幕 |

## 编写建议

1. **8–14 段**：过少则滚动粒度粗，过多则录屏难以同步
2. **expected_duration 合理**：参考每段文字朗读约 3–4 字/秒
3. **page_target 具体**：用自然语言描述 UI 位置，便于录屏时对照
4. **scroll_action 与 notes 配合**：录屏前在步骤 6 校准过的策略写入对应段
5. **不要逐字念界面**：`text` 应是讲解性口语，而非原文复制

## run.json 关联

`run.json` 记录运行元数据，与 `segments.json` 互补：

| 字段 | 说明 |
|------|------|
| `run_id` | 运行 ID |
| `created_at` | 创建时间 |
| `status` | `initialized` → `narrated` → `ingested` → `composed` |
| `voice_provider` | 如 `Edge TTS` |
| `voice_id` | 如 `zh-CN-YunxiNeural` |
| `voice_rate` | 如 `-3%` |
| `voice_style` | 如 `中文自然男声` |
| `target_description` | 用户目标描述 |

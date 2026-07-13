# 声音预设

Screencast Explainer 使用 **Edge TTS** 作为默认语音合成引擎。声音配置可在初始化或生成旁白时指定。

## 默认配置

| 字段 | 默认值 | 说明 |
|------|--------|------|
| `voice_provider` | `Edge TTS` | 语音合成引擎 |
| `voice_id` | `zh-CN-YunxiNeural` | 中文自然男声，验证效果较好 |
| `voice_style` | `中文自然男声` | 人类可读描述 |
| `voice_rate` | `-3%` | 略慢于标准语速，适合讲解 |

当 `doctor.py` 检测到 Edge TTS 可用且用户未指定声音时，自动选用上述默认值。

## 可配置字段

以下字段写入 `run.json`，也可通过 CLI 参数覆盖：

| 字段 | CLI 参数 | 说明 |
|------|----------|------|
| `voice_id` | `--voice-id` | Edge TTS 语音 ID |
| `voice_rate` | `--voice-rate` | 语速调整，如 `-3%`、`+10%` |
| `voice_provider` | — | 当前仅支持 Edge TTS |
| `voice_style` | — | 描述性标签，写入 `run.json` 供交付参考 |

## CLI 用法示例

```bash
# 初始化时使用默认声音
python3 <skill-root>/scripts/init_run.py \
  --output-dir ./outputs/<run-id>

# 初始化时指定声音
python3 <skill-root>/scripts/init_run.py \
  --output-dir ./outputs/<run-id> \
  --voice-id zh-CN-YunxiNeural \
  --voice-rate -3%

# 生成旁白时覆盖声音（需与 init_run 一致或在此步骤指定）
python3 <skill-root>/scripts/build_narration.py \
  --output-dir ./outputs/<run-id> \
  --voice-id zh-CN-YunxiNeural \
  --voice-rate -3% \
  --gap 0.45
```

`--gap 0.45` 控制段间静音间隔（秒），默认 0.45。

## 常用中文语音 ID

| voice_id | 风格 | 适用场景 |
|----------|------|----------|
| `zh-CN-YunxiNeural` | 自然男声（默认） | 桌面 App 讲解、教程 |
| `zh-CN-XiaoxiaoNeural` | 自然女声 | 用户明确要求女声 |
| `zh-CN-YunyangNeural` | 新闻播报男声 | 正式、新闻风格 |
| `zh-CN-XiaoyiNeural` | 活泼女声 | 轻松、年轻化内容 |

完整列表可通过 Edge TTS 命令行查询：

```bash
edge-tts --list-voices | grep zh-CN
```

## 缺失 Edge TTS 时的处理

若 `doctor.py` 报告 `edge_tts: unavailable`：

- Agent **不得**静默跳过配音步骤
- 应告知用户 Edge TTS 不可用，说明安装方式：`pip install edge-tts`
- 在 Edge TTS 恢复可用之前，无法完成标准流水线

## 交付时记录

步骤 9 交付时，Agent 应报告实际使用的：

- `voice_provider`
- `voice_id`
- `voice_style`
- `voice_rate`

这些信息保存在 `./outputs/<run-id>/run.json` 中。

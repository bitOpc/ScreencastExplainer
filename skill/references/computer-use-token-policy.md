# Computer Use 省 Token 策略

本文档是 **Agent 操作建议 + 正式录制路径约束**。精简/常态/浪费不是 CLI 参数；真正的省 token 路径是：校准后写 `actions.json`，正式录制时由 `timeline_player.py` 直连 cua-driver 回放动作。

代码里不会出现 `精简` / `常态` / `浪费` 枚举；Agent 在步骤 6（校准 UI 动作）时按下列策略控制截图，步骤 7 必须使用本地动作时间轴，避免录屏期间反复调用 LLM `computer_use` 工具。

## 背景

Computer Use 每次 `capture` / 截图会消耗大量 context token（Hermes 文档量级：约 1500 token/张，且会保留最近若干张）。  
录屏阶段画面由 `run_recording.py` 负责：`record_window.py` 录屏，`timeline_player.py` 通过 cua-driver 回放 `actions.json`。**不必**为确认画面而频繁截图。

## 三档策略（Agent 自选）

| 策略 | 适用场景 | capture 频率 | 全流程 token 粗估* |
|------|----------|--------------|-------------------|
| **精简** | 短稿、PPT/PDF/文档等可预编排场景 | 校准阶段少量 capture；录屏中**不调用 LLM computer_use** | 取决于校准轮次，通常显著低于逐步操作 |
| **常态** | 默认；中等复杂 UI | 校准阶段按关键动作确认；录屏中仍使用 `actions.json` 回放 | 主要消耗在校准和脚本撰写 |
| **浪费** | 复杂 UI、多面板切换、反复试错 | 校准阶段反复 capture，或录屏中仍逐步调用 LLM `computer_use` | 可能出现百万到千万级 cache-read |

\* 含脚本撰写、分段、旁白生成与合成；实际因模型与平台而异，仅作量级参考。

## 精简模式（推荐默认）

1. 步骤 6：对每类关键动作最多测少量样本，优先用 `key` / `hotkey`，其次 `scroll` / `click`。
2. 步骤 6：把成功动作写入 `actions.json`，并用 `timeline_player.py --dry-run` 预览。
3. 步骤 7：录屏开始后使用 `run_recording.py`，**录屏期间禁止**为推进画面而调用 LLM `computer_use`。
4. 录屏结束后用 `ingest_capture.py` 校验时长；失败再针对性重录，而不是录屏中反复截图。

## 常态模式

- 步骤 6：围绕动作类别做关键点确认，必要时 capture。
- 步骤 7：仍然使用 `actions.json` 回放，不在录屏期间边看边操作。
- 仍禁止「每步操作都截图」。

## 浪费模式（避免）

- 录屏全程高频 capture，或每个动作都让 LLM 调一次 `computer_use` → token/cache-read 暴涨，且与 `timeline_player.py` 重复。
- 仅在用户明确要求「录屏过程中实时盯画面」且接受高 token 消耗时考虑。

## 与代码的对应关系

| 概念 | 是否在代码中 |
|------|----------------|
| `record_window.py` 单窗口录屏 | ✅ 有 |
| `timeline_player.py` / `run_recording.py` 本地动作回放 | ✅ 有 |
| `doctor.py` 依赖检查 | ✅ 有 |
| 精简 / 常态 / 浪费 | ❌ 无；见本文档，由 Agent 执行时自律 |

用户若问「有没有省 token 模式」，回答：**没有模式开关；正式录屏默认就应使用 `actions.json` + `run_recording.py` 的低 token 路径。**

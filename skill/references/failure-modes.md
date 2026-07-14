# 常见失败模式

Screencast Explainer 在端到端执行中可能遇到以下四类失败。Agent 应在交付前识别并处理，**不可将就交付**。

---

## 失败模式 1：视频只有字幕，没有真实 App 界面

### 症状

- 最终 `video/final.mp4` 长时间显示黑底或纯色背景
- 画面中没有目标 App 的真实 UI
- 仅有旁白与硬字幕

### 原因

- 录错了 `window_id`，或窗口已关闭
- 未授予「屏幕录制」权限给运行 `screencapture` 的宿主进程
- 未实际生成 `capture/raw.mp4`，或用了错误来源（整屏/黑屏）

### 处理

**不可交付。** 必须：

1. 确认宿主（终端 / Cursor / Hermes）已获屏幕录制权限
2. 用 `list_windows` 重新确认目标 `window_id`
3. 用 `record_window.py` 重新执行步骤 7（单窗口录屏）
4. 重跑 `ingest_capture.py` → `compose_video.py`

说明：单窗口录屏**不要求**目标 App 始终在前台；后台录制是支持的。

---

## 失败模式 2：界面只动了一点，大部分时间停留首屏

### 症状

- 视频开头几秒有 App 界面，之后长时间停在同一屏
- 旁白已在讲解后续内容，画面仍显示文档/页面开头
- 滚动/翻页几乎未发生

### 原因

- 滚动策略未校准或无效（PageDown/滚轮未生效）
- 录屏时未按 `segments.json` 时间轴推进画面
- 目标 App 焦点丢失

### 处理

1. 回到步骤 6，重新校准页面推进策略
2. 依次测试 PageDown → 滚轮 → 混合 → 点击/切标签
3. 每次测试后确认 UI 状态确实变化
4. 重新录屏（步骤 7）
5. 重跑 ingest → compose

---

## 失败模式 3：旁白已在后半段，画面仍在前半段

### 症状

- 旁白正在讲解文档中段或后段内容
- 画面仍显示文档开头或前半部分
- 讲解节奏与界面节奏明显脱节

### 原因

- 录屏时未将 `segments.json` 各段的 `expected_duration` / `actual_duration` 与滚动动作绑定
- 滚动时机滞后或提前
- 分段数过少，无法精细控制推进

### 处理

1. 检查 `segments.json`：每段是否包含明确的 `page_target` 与 `scroll_action`
2. 必要时增加分段（8–14 段范围内调整）
3. 重新生成旁白（`build_narration.py`）以更新时间轴
4. 录屏时严格按各段 `start`/`end` 时间推进画面
5. 重新录屏并重跑 ingest → compose

---

## 失败模式 4：`ingest_capture.py` 报告音视频时长不匹配

### 症状

- 运行 `ingest_capture.py` 时退出并报错
- 提示 `capture/raw.mp4` 与 `narration.wav` 时长差异超过 ±0.5 秒

### 原因

- 录屏过早结束或过长
- 录屏过程中出现长时间停顿
- 旁白重新生成后未重新录屏

### 处理

**方案 A（推荐）：重新录屏**

1. 确认 `narration.wav` 时长（`ffprobe`）
2. 按旁白时长重新录屏，确保起止同步
3. 重跑 `ingest_capture.py` → `compose_video.py`

**方案 B：调整旁白**

1. 若录屏时长正确但旁白过长/过短，修改 `segments.json` 后重跑 `build_narration.py`
2. 重新录屏以匹配新旁白时长
3. 重跑 ingest → compose

**不可**忽略时长错误强行合成，否则最终视频将出现音画不同步。

---

## 交付前自检清单

Agent 在步骤 9 交付前，应目视确认：

- [ ] 视频包含真实 App 界面（非黑底）
- [ ] 开头、中段、结尾画面均有推进
- [ ] 旁白内容与当前画面位置大致对应
- [ ] `ingest_capture.py` 与 `compose_video.py` 均已成功执行
- [ ] `run.json` 状态为 `composed`

任一未通过 → 参照上表对应模式处理，**不得交付**。

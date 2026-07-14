---
name: screencast-explainer
description: >
  用 Computer Use 驱动桌面 App 完成真实界面实时录屏，围绕界面内容生成
  带旁白与硬字幕的讲解视频。适用于 Obsidian、浏览器、IDE、办公软件等
  可视化应用。执行前必须做依赖检查；先写脚本再录屏；画面必须随讲解推进。
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [screencast, video, computer-use, narration, macos]
    category: media
  openclaw:
    homepage: "https://github.com/bitOpc/ScreencastExplainer"
triggers:
  - 录屏讲解
  - 讲解视频
  - screencast explainer
  - 界面讲解
  - obsidian://
  - 桌面 App 讲解
---

# Screencast Explainer

这个 skill 的目标，是让 Agent 学会一件稳定的事情：

通过 **Computer Use** 驱动桌面 App，生成「真实应用界面讲解视频」，而不是黑底字幕视频。

## 适用场景

- 用户希望对某个桌面 App 的界面内容做讲解视频
- 用户要求画面跟随讲解推进而切换、滚动、翻页或操作
- 用户要求口播简洁，不逐字念文章
- 用户可能给出：
  - `obsidian://` 链接
  - 某个桌面 App 名称
  - 某个网页或本地文件
  - 某个软件里的操作流程

## 成功标准

1. 目标 App 或目标内容成功在前台打开
2. 讲解脚本先生成，再根据脚本反推滚动节奏
3. 视频画面是真实 App 界面
4. 画面随着讲解推进而推进
5. 最终输出成片、音频、字幕及交付清单

## 参考文档

执行前或遇到问题时，请查阅 `references/` 目录：

| 文件 | 用途 |
|------|------|
| [standard-pipeline.md](references/standard-pipeline.md) | Computer Use + Python + ffmpeg 三段式职责 |
| [voice-presets.md](references/voice-presets.md) | 默认声音与可配置字段 |
| [failure-modes.md](references/failure-modes.md) | 四类常见失败模式与处理 |
| [segment-schema.md](references/segment-schema.md) | `segments.json` 字段说明与示例 |
| [install-paths.md](references/install-paths.md) | 四平台安装路径与 `install.sh` 用法 |
| [recording-window.md](references/recording-window.md) | 单窗口后台录屏（`screencapture -v -l`） |
| [computer-use-token-policy.md](references/computer-use-token-policy.md) | Computer Use 省 token 策略（精简/常态/浪费，**非代码开关**） |

## 安装

用户可通过一句话让 Agent 安装本 skill：

```
帮我安装 Screencast Explainer：https://raw.githubusercontent.com/bitOpc/ScreencastExplainer/main/docs/install.md
```

Agent 应**只装到当前会话所在平台**（见 `docs/install.md` Step 4），不要默认 `./install.sh` 装四路。完整步骤见仓库 `docs/install.md`；本地已 clone 时也可直接读该文件。

## 依赖约定

这个 skill 不是纯文本 skill，它依赖外部工具链。

### 脚本侧依赖（由 `doctor.py` 检查）

- `python3`
- `ffmpeg`
- `ffprobe`
- `screencapture`（macOS 单窗口录屏）
- `Edge TTS`（Python 包 `edge-tts`）
- 可用中文字体（Pillow 探测）

### Agent 侧依赖（Agent 自行报告）

- **Computer Use**：能否读取并操作目标 App（后台操作即可，不必始终置前）
- **Target App**：能否打开到正确界面
- **Screen Recording Permission**：授予**运行 screencapture 的宿主**（终端 / Cursor / Hermes），用于单窗口录屏

如果这些依赖不成立，Agent 可能「知道流程」，但实际无法执行。因此 **必须先做依赖检查，不允许跳过**。

运行依赖检查：

```bash
python3 <skill-root>/scripts/doctor.py --json
```

Agent 额外输出：

- `Computer Use`: available / unavailable
- `Target App`: available / unavailable
- `Screen Recording Permission`: granted / denied

任一不可用 → **中止任务并说明原因**。

## 推荐声音配置

详见 [voice-presets.md](references/voice-presets.md)。

默认配置（Edge TTS 可用且用户未指定时）：

- `voice_provider = Edge TTS`
- `voice_id = zh-CN-YunxiNeural`
- `voice_style = 中文自然男声`
- `voice_rate = -3%`

## 标准流水线概览

详见 [standard-pipeline.md](references/standard-pipeline.md)。

```
doctor → init_run
→ [Agent 写 script.md + segments.json]
→ build_narration
→ [Agent: 取得 window_id；record_window.py 单窗口录屏 + Computer Use 后台推进 UI → capture/raw.mp4]
→ ingest_capture → compose_video
→ 交付
```

## 强制工作流

### 0. 先做依赖检查（不可跳过）

```bash
python3 <skill-root>/scripts/doctor.py --json
```

Agent 额外报告：

- `Computer Use`: available / unavailable
- `Target App`: available / unavailable
- `Screen Recording Permission`: granted / denied
- `Selected Voice`: 当前将使用的声音

如果 `Edge TTS` 可用且用户没有指定声音，默认选 `zh-CN-YunxiNeural` @ `-3%`。

**任一关键依赖不可用 → 中止并说明。**

### 1. 先理解输入

从用户请求中抽取：

- 目标 App 或目标内容入口
- 开场自我介绍
- 系列介绍
- 正式开讲句
- 目标时长
- 语音要求
- 是否硬字幕

没有给全时，使用以下默认值：

- 讲解风格：简洁解释
- 字幕：硬字幕（开启）
- 声音：`Edge TTS / zh-CN-YunxiNeural / -3%`

### 2. 打开目标界面（Computer Use）

必须优先把目标 App 打开到用户需要讲解的正确界面。

例如：

- **Obsidian**：打开 `obsidian://...`
- **浏览器**：打开目标网页
- **IDE**：打开目标项目和文件
- **Office 软件**：打开目标文档或表格

通用动作：

1. 打开目标资源
2. 激活目标 App
3. 获取当前 app state
4. 确认标题栏与正文/主区域确实对应目标内容

### 3. 先写脚本（禁止先录屏）

**禁止先录屏再想讲什么。**

在输出目录写入 `script.md`。脚本要求：

- 开头自我介绍必须与用户要求一致
- 系列介绍要简短
- 正式开讲要明确指出当前讲解对象
- **不要逐字朗读界面内容**
- 总时长尽量接近目标

### 4. 脚本分段并初始化运行

把脚本拆成 **8 到 14 段**，写入 `segments.json`（`status: draft`）。

字段说明见 [segment-schema.md](references/segment-schema.md)。

每段至少包含：

- `text`
- `expected_duration`
- `page_target`
- `scroll_action`
- `ui_target`（推荐）

然后初始化运行目录：

```bash
python3 <skill-root>/scripts/init_run.py \
  --output-dir ./outputs/<run-id> \
  [--voice-id zh-CN-YunxiNeural] \
  [--voice-rate -3%]
```

### 5. 生成音频与字幕

```bash
python3 <skill-root>/scripts/build_narration.py \
  --output-dir ./outputs/<run-id> \
  [--voice-id zh-CN-YunxiNeural] \
  [--voice-rate -3%] \
  [--gap 0.45]
```

输出：

- `narration.wav`
- `captions.srt`
- `captions.ass`
- 更新后的 `segments.json`（`status: narrated`，含 `start` / `end` / `actual_duration`）

记录实际使用的 `voice_provider`、`voice_id`、`voice_style`、`voice_rate`。

### 6. 校准页面推进策略（Computer Use，录屏前必做）

**省 token：** 默认按 [computer-use-token-policy.md](references/computer-use-token-policy.md) 的「精简」策略执行——校准阶段少截图，录屏中不为看画面而 capture。精简/常态/浪费是 Agent 操作档位，**不是** CLI 或 Python 模式。

必须先做小测试，再决定用哪种方式推进画面。

依次测试：

1. `PageDown`
2. 滚轮事件
3. 混合方案
4. 必要时使用点击、切标签、切面板、切页签、切视图

每次测试后都要重新获取目标 App 状态，检查画面是否真的推进。

**如果画面未推进：**

- 不要开始整段录屏
- 立刻更换策略

### 7. 单窗口实时录屏（唯一采集模式）

**标准做法：** 用 `record_window.py`（底层 `screencapture -v -l <window_id>`）录制**单个应用窗口**的连续视频；同时用 Computer Use **后台**滚动/操作（不要为录屏抢前台）。

详见 [recording-window.md](references/recording-window.md)。

```bash
# 先取得目标窗口 window_id（Computer Use / cua-driver list_windows）
python3 <skill-root>/scripts/record_window.py \
  --output-dir ./outputs/<run-id> \
  --window-id <WINDOW_ID>
```

**并行操作：**

1. `record_window.py` 按旁白时长启动录屏（写入 `capture/raw.mp4`）
2. 录制进行中：Computer Use 按 `segments.json` 时间轴执行 `scroll` / `page_down` / `click` 等
3. `raise_window` 默认 **false**；除非用户明确要求，不要把目标窗口提到前台

**要求：**

- 画面必须是目标 App **窗口内容**（不是整屏桌面）
- 画面必须随旁白段落推进而滚动/翻页/切换
- 录屏时长应与 `narration.wav` 大致一致（脚本会向上取整秒数）
- 必须是连续视频，**禁止**截图拼凑

**不支持：**

- 连续采帧离线合成
- 以整屏录制 + crop 冒充单窗口（遮挡时会录错）
- cua-driver `record_video`（主显示器）作为正式交付路径

失败时调整 window_id / 权限 / 滚动策略后重新录制。

### 8. 合成

```bash
python3 <skill-root>/scripts/ingest_capture.py \
  --output-dir ./outputs/<run-id>

python3 <skill-root>/scripts/compose_video.py \
  --output-dir ./outputs/<run-id> \
  [--crf 18]
```

- `ingest_capture.py`：校验 `capture/raw.mp4` 与 `narration.wav` 时长（容差 ±0.5s），标准化为 `video/normalized.mp4`
- `compose_video.py`：混合旁白 + 硬字幕 → `video/final.mp4`

若 `ingest_capture.py` 报告音视频时长不匹配 → 见 [failure-modes.md](references/failure-modes.md) 模式 4。

### 9. 交付

最终回答中应包含：

- 脚本路径（`script.md`）
- 音频路径（`narration.wav`）
- 字幕路径（`captions.srt` / `captions.ass`）
- 成片路径（`video/final.mp4`）
- 时长
- 实际使用声音

**不做自动化关键帧抽帧验收。** 交付前 Agent 应目视确认画面随讲解推进（参见 [failure-modes.md](references/failure-modes.md)）。

## 常见失败模式

详见 [failure-modes.md](references/failure-modes.md)。

| # | 模式 | 处理 |
|---|------|------|
| 1 | 视频只有字幕，没有真实 App 界面 | 不可交付，重新录屏 |
| 2 | 界面只动了一点，大部分时间停留首屏 | 重新校准滚动，重新录屏 |
| 3 | 旁白已在后半段，画面仍在前半段 | 重新绑定分段与时间轴，重新录屏 |
| 4 | `ingest_capture.py` 报告音视频时长不匹配 | 重新录屏或裁剪旁白，重跑 ingest |

## 输出目录结构

```
outputs/<run-id>/
├── run.json
├── script.md
├── segments.json
├── narration.wav
├── captions.srt
├── captions.ass
├── capture/
│   └── raw.mp4
└── video/
    ├── normalized.mp4
    └── final.mp4
```

## 禁止事项

- 不得使用连续采帧 / 截图拼视频替代单窗口实时录屏
- 不得使用整屏录制 + crop、或 cua-driver 整屏 `record_video` 作为正式成片来源
- 不得使用 `verify_keyframes.py` 或类似抽帧验收脚本
- 不得先录屏后写脚本
- 不得交付黑底纯字幕视频

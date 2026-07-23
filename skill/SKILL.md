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
6. 若用户在本片启用了真人讲解，成片右下角应有圆形真人画中画（口型跟随旁白）

## 参考文档

执行前或遇到问题时，请查阅 `references/` 目录：

| 文件 | 用途 |
|------|------|
| [standard-pipeline.md](references/standard-pipeline.md) | Computer Use + Python + ffmpeg 三段式职责 |
| [voice-presets.md](references/voice-presets.md) | 默认声音与可配置字段 |
| [failure-modes.md](references/failure-modes.md) | 四类常见失败模式与处理 |
| [segment-schema.md](references/segment-schema.md) | `segments.json` 字段说明与示例 |
| [action-timeline.md](references/action-timeline.md) | `actions.json` 通用 UI 动作时间轴 |
| [install-paths.md](references/install-paths.md) | 四平台安装路径与 `install.sh` 用法 |
| [recording-window.md](references/recording-window.md) | 单窗口后台录屏（`screencapture -v -l`） |
| [presenter-avatar.md](references/presenter-avatar.md) | 可选真人讲解：安装/成片确认剧本、耗时估算、半身照 |
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

## 输出目录约定（强制）

**所有运行产物必须写在当前 session 的工作目录下**，不要使用 skill 安装目录：

| 用途 | 正确 | 错误 |
|------|------|------|
| 运行目录 | `<session-cwd>/outputs/<run-id>/` | `~/.screencast-explainer/outputs/` |
| 脚本路径 | `<skill-root>/scripts/...` | 在 `outputs/` 下自写 `build_*.py` |

规则：

1. 任务开始时确认 **session 工作目录**（`pwd`）；所有 `--output-dir` 使用 `$PWD/outputs/<run-id>` 或 `./outputs/<run-id>`。
2. **禁止**把 `~/.screencast-explainer/`、`~/.hermes/`、`<skill-root>/` 当作运行输出根目录（那是源码与 skill 安装位置）。
3. 若用户未指定项目目录，使用当前 session 的 `cwd`；不要自行切换到 skill 仓库。

```bash
RUN_ID="<topic>-$(date +%Y%m%d-%H%M%S)"
RUN="$PWD/outputs/$RUN_ID"
mkdir -p "$RUN"
```

运行依赖检查：

```bash
python3 <skill-root>/scripts/doctor.py --json
```

Agent 额外输出：

- `Computer Use`: available / unavailable
- `Target App`: available / unavailable
- `Screen Recording Permission`: granted / denied

任一不可用 → **中止任务并说明原因**。

## 声音配置（强制）

详见 [voice-presets.md](references/voice-presets.md)。

默认配置：

- `voice_provider = Edge TTS`
- `voice_id = zh-CN-YunxiNeural`
- `voice_style = 中文自然男声`
- `voice_rate = -3%`

**硬规则（违反即错误）：**

1. 用户未明确要求换声时，必须使用默认 `zh-CN-YunxiNeural`；`init_run` / `build_narration` 可不传 `--voice-id`，或只传该默认值。
2. **禁止**根据角色名、自我介绍、脚本人设推断音色。「艾达」「助手」等名字 ≠ 女声要求。
3. 用户说「用 skill 默认 / 默认声音」= 强制 `zh-CN-YunxiNeural`，不得覆盖。
4. **仅当**用户明确说「女声 / Xiaoxiao / 换某个 voice_id」时才改 `voice_id`。
5. 步骤 0 或步骤 4 后回显一行（不打断、不 clarify）：`Selected Voice: Edge TTS / zh-CN-YunxiNeural / -3%（默认男声）`。
6. `run.json` 的 `voice_style` 必须与实际 `voice_id` 一致。

## 标准流水线概览

详见 [standard-pipeline.md](references/standard-pipeline.md)。

```
doctor → init_run
→ [Agent 写 script.md + segments.json]
→ build_narration
→ [可选：本片真人讲解确认 → build_avatar.py]
→ [Agent: 校准 UI 动作并写 actions.json]
→ [run_recording.py: record_window.py 单窗口录屏 + timeline_player.py 直连 cua-driver 回放 UI → capture/raw.mp4]
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

如果 `Edge TTS` 可用且用户没有指定声音（或说「用默认」），强制选 `zh-CN-YunxiNeural` @ `-3%`，并回显 `Selected Voice`。不得因「艾达」等人设改女声。

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
- `scroll_action`（兼容字段；正式回放以 `actions.json` 为准）
- `ui_target`（推荐）

然后初始化运行目录（`RUN` 为当前 session 工作目录下的路径，见上文「输出目录约定」）：

```bash
python3 <skill-root>/scripts/init_run.py \
  --output-dir "$RUN" \
  [--voice-id zh-CN-YunxiNeural] \
  [--voice-rate -3%]
```

### 5. 生成音频与字幕

**必须且只能**使用官方脚本 `build_narration.py` 生成 `narration.wav`、`captions.srt`、`captions.ass`：

```bash
python3 <skill-root>/scripts/build_narration.py \
  --output-dir "$RUN" \
  [--voice-id zh-CN-YunxiNeural] \
  [--voice-rate -3%] \
  [--gap 0.45]
```

**禁止：**

- 在 `outputs/` 下自写 `build_narration_*.py`、`build_narration_say.py` 等替代脚本
- 手写或改写 `captions.ass` 的 Style 行（字体、字号由 `lib/subtitles.py` 统一生成：`STHeiti` 42px）
- Edge TTS 失败时擅自降级到 `say` 而不告知用户；应先重试或请用户处理网络，再决定是否中止

若 `build_narration.py` 报错，修复环境后重跑同一脚本，**不要**换一套自制流水线。

输出：

- `narration.wav`（TTS 实际时长拼接，段间含 `gap` 静音；**不会**为凑 `expected_duration` 而加速）
- `captions.srt` / `captions.ass`（**单行硬字幕**：每个 `segments.json` 段落会按字数比例拆成多条短时序字幕，**同屏只显示一行**）
- 更新后的 `segments.json`（`status: narrated`，含 `start` / `end` / `actual_duration`）

**字幕硬规则：**

1. 硬字幕**同屏最多 1 行**；禁止整段旁白一次性烧录成一条长字幕。
2. 拆分由 `lib/subtitles.py` 自动完成：`segments.json` 仍按段落写旁白，字幕文件会展开为多条单行 cue。
3. 已有 narrated 产物只需重生成字幕时：

```bash
python3 <skill-root>/scripts/build_narration.py \
  --output-dir "$RUN" \
  --captions-only
```

然后重跑 `compose_video.py` 即可，无需重录。

记录实际使用的 `voice_provider`、`voice_id`、`voice_style`、`voice_rate`。

**注意：** `actions.json` 的 `at` 必须对齐 narrated 后的 `start`/`end`，不要用草稿里的 `expected_duration` 推算。

### 5b. 可选 — 真人讲解画面（`build_avatar.py`）

**前置：** `presenter.json` 中 `enabled=true` 且 `installed=true`。否则跳过，行为与现网一致。

`build_narration.py` 完成后，**在录屏之前**，按 [presenter-avatar.md](references/presenter-avatar.md) 执行成片三步确认：

1. 本片是否启用真人讲解？
2. 告知本片预估耗时（CUDA：旁白秒数 × 2–4 / 60 分钟；无 CUDA：「可能数小时」）并获用户确认
3. 半身照：沿用 / 更换 / 首次收集 → 写入 `$RUN/avatar.json`

**硬规则（违反即错误）：**

1. **禁止**未获本片启用确认就调用 `build_avatar.py`
2. **禁止**未告知耗时并获确认就开始生成
3. **禁止**无合格半身照或占位图生成 avatar
4. **禁止**静默安装 SadTalker（安装见 `docs/install.md` Step 6，`install_presenter.sh --yes`）
5. 用户取消或生成失败 → 可 `--no-avatar` 继续合成，仍须交付无角色成片

用户确认启用后：

```bash
python3 <skill-root>/scripts/build_avatar.py --output-dir "$RUN"
```

输出 `video/avatar.mp4`（无音轨）与 `video/avatar.report.json`。随后进入步骤 6 校准 UI 动作。

### 6. 校准 UI 动作并写入 `actions.json`（Computer Use，录屏前必做）

**省 token：** 默认按 [computer-use-token-policy.md](references/computer-use-token-policy.md) 的「精简」策略执行——校准阶段少截图，录屏中不为看画面而 capture。精简/常态/浪费是 Agent 操作档位，**不是** CLI 或 Python 模式。

必须先做小测试，再把成功动作写入 `$RUN/actions.json`。字段见 [action-timeline.md](references/action-timeline.md)。

**录屏前必须确认画面在文档/内容顶部：**

1. `actions.json` 第一个事件应为 `{"at": 0.0, "action": "key", "key": "Home"}`（或 Obsidian 等场景用已验证可回到顶部的快捷键）
2. 在 Obsidian 阅读视图中，`Home` 可能无效；校准阶段必须**目视确认**已回到顶部，必要时改用 `scroll` 小步上滚或 `cmd+up` 等已验证动作
3. 第一段旁白对应的内容必须在首屏可见；不要在前 30–60 秒安排 `scroll_action: none` 却讲解需要往下看的内容

按键名使用 cua-driver 认可的写法：`Home`、`PageDown`、`End`（首字母大写，与历史成功任务一致）。

优先级：

1. `key` / `hotkey`：PPT、PDF、翻页、快捷键场景优先
2. `scroll`：文档、网页、列表
3. `click` / `double_click` / `right_click`：按钮、标签页、链接、项目打开
4. `drag` / `type_text`：仅在任务需要时使用

校准阶段允许少量 `computer_use`：先 `capture(mode="som")` 理解界面，后续优先 `mode="ax"` 或轻量状态检查。**正式录制阶段不再逐步调用 LLM `computer_use` 工具**，而由 `timeline_player.py` 直连 cua-driver 回放。

**如果画面未推进：**

- 不要开始整段录屏
- 立刻更换策略
- 更新 `actions.json` 后先执行 dry-run：

```bash
python3 <skill-root>/scripts/timeline_player.py \
  --actions ./outputs/<run-id>/actions.json \
  --output-dir ./outputs/<run-id> \
  --dry-run
```

### 7. 单窗口实时录屏 + 本地动作时间轴回放（唯一采集模式）

**标准做法：** 用 `run_recording.py` 同时启动：

1. `record_window.py`（底层 `screencapture -v -l <window_id>`）录制**单个应用窗口**的连续视频
2. `timeline_player.py` 按 `actions.json` 直连 cua-driver 执行后台 UI 动作

详见 [recording-window.md](references/recording-window.md)。

```bash
# 先取得目标窗口 window_id（Computer Use / cua-driver list_windows）
export PATH="$HOME/.local/bin:$PATH"
python3 <skill-root>/scripts/run_recording.py \
  --output-dir ./outputs/<run-id> \
  --window-id <WINDOW_ID>
```

**录屏硬规则（违反即错误）：**

1. **只允许**上述一条官方命令启动录屏；**禁止**在 `outputs/` 下自写 `record_*.py`、`capture_movie.py` 等替代脚本。
2. **禁止**给 `run_recording.py` 传 `--duration`（该参数仅存在于底层 `record_window.py`；编排脚本会从 `narration.wav` 自动推断时长）。
3. 使用 **terminal 一次阻塞等待**（timeout ≥ 900s），等命令自然结束；**禁止** `cmd &`、**禁止** `process` 工具轮询录屏状态。
4. 录屏结束后检查 `capture/recording.report.json`：`status` 必须为 `ok`，且 `video_duration` 与 `audio_duration` 偏差 ≤ 0.5s。
5. 若 `run_recording.py` 失败，修复环境/权限/window_id 后**重跑同一命令**；不要换自研录屏编排。

**要求：**

- 录屏中禁止为了推进画面而逐步调用 LLM `computer_use`
- `actions.json` 的动作默认 `delivery_mode=background`
- `foreground` 只允许作为明确兜底，并需传 `--allow-foreground`
- 画面必须是目标 App **窗口内容**（不是整屏桌面）
- 画面必须随旁白段落推进而滚动/翻页/点击/切换
- 录屏时长应与 `narration.wav` 大致一致（脚本会向上取整秒数）
- 必须是连续视频，**禁止**截图拼凑

`run_recording.py` 会写入 `actions.report.json`，用于交付时说明回放动作是否执行。

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
  [--crf 18] \
  [--with-avatar | --no-avatar]

python3 <skill-root>/scripts/build_cover.py \
  --output-dir ./outputs/<run-id>
```

- `ingest_capture.py`：校验 `capture/raw.mp4` 与 `narration.wav` 时长（容差 ±0.5s），标准化为 `video/normalized.mp4`
- `compose_video.py`：混合旁白 + 硬字幕（+ 可选 avatar 画中画）→ `video/final.mp4`
- `build_cover.py`：从成片帧 + 运行元数据生成 `video/cover.png`（暗色遮罩 + 中英文标题，风格参考 YouTube 封面）

若 `ingest_capture.py` 报告音视频时长不匹配 → 见 [failure-modes.md](references/failure-modes.md) 模式 4。

### 9. 交付

最终回答中应包含：

- 脚本路径（`script.md`）
- 动作时间轴路径（`actions.json`）
- 动作回放报告（`actions.report.json`）
- 音频路径（`narration.wav`）
- 字幕路径（`captions.srt` / `captions.ass`）
- 成片路径（`video/final.mp4`）
- 若启用真人讲解：`video/avatar.mp4`、`video/avatar.report.json`
- 封面路径（`video/cover.png`）
- 时长
- 实际使用声音

**成片链接格式（Hermes 媒体播放）：** `MEDIA:` 必须单独占一行，使用绝对路径，**不要**包在 markdown 粗体、反引号或链接语法里：

```
成片：video/final.mp4

MEDIA:/absolute/path/to/outputs/<run-id>/video/final.mp4
```

错误示例（会导致链接乱码）：`` **`MEDIA:...`** ``、`[File: final.mp4](...)`

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
├── actions.json
├── actions.report.json
├── narration.wav
├── captions.srt
├── captions.ass
├── avatar.json                 # 可选：本片真人讲解确认
├── capture/
│   └── raw.mp4
└── video/
    ├── normalized.mp4
    ├── final.mp4
    ├── cover.png
    └── cover.report.json
```

## 禁止事项

- 不得使用连续采帧 / 截图拼视频替代单窗口实时录屏
- 不得使用整屏录制 + crop、或 cua-driver 整屏 `record_video` 作为正式成片来源
- 不得使用 `verify_keyframes.py` 或类似抽帧验收脚本
- 不得先录屏后写脚本
- 不得交付黑底纯字幕视频
- 不得把运行产物写入 `~/.screencast-explainer/outputs/` 或 skill 安装目录
- 不得自写旁白/字幕生成脚本或手写 `captions.ass` 样式
- 不得用 markdown 格式包裹 `MEDIA:` 交付行
- 不得根据「艾达」等角色名推断女声；未明确要求换声时不得覆盖默认 `zh-CN-YunxiNeural`

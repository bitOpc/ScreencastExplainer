# 单窗口后台录屏

本技能对桌面 App 讲解视频的**标准采集方式**：用 macOS 自带 `screencapture` 对 **单个 window_id** 做连续视频录制（真录屏，不是截图拼凑），并与 `timeline_player.py` 直连 cua-driver 的 **后台动作回放**并行。

## 为什么不用 cua-driver 的 record_video

| 方式 | 单窗口 | 连续视频 | 后台不抢前台 | Skill 中角色 |
|------|--------|----------|--------------|--------------|
| `cua-driver start_recording(record_video=true)` | ❌ 主显示器整屏 | ✅ | ✅ | 不推荐为主路径 |
| 整屏再 crop | 伪单窗口（遮挡会录错） | ✅ | ✅ | 禁止作为正式方案 |
| **`screencapture -v -l <window_id>`** | ✅ | ✅ | ✅ | **首选** |
| trajectory 窗口截图拼成 mp4 | 窗口级 | ❌ | ✅ | **禁止** |

## 职责划分

| 组件 | 职责 |
|------|------|
| Computer Use / cua-driver | 录屏前打开内容、校准动作、生成 `actions.json` |
| `timeline_player.py` → cua-driver | 录屏中按 `actions.json` 后台推进 UI（默认 `delivery_mode=background`） |
| `record_window.py` → `screencapture` | 按 window_id 录制真实连续视频 → `capture/raw.mp4` |
| `ingest_capture.py` / `compose_video.py` | 时长校验、旁白与硬字幕合成 |

## 权限

录屏归属 **发起 `screencapture` 的进程**（终端 / Cursor / Hermes 宿主），不是 CuaDriver。

系统设置 → 隐私与安全性 → **屏幕录制** → 勾选实际跑 Agent / 终端的应用。

CuaDriver 的屏幕录制权限只服务于 Computer Use 截图，与本路径独立。

## 推荐工作流

```bash
# 1. 依赖检查（含 screencapture）
python3 <skill-root>/scripts/doctor.py --json

# 2. 获取目标窗口 ID（Computer Use / cua-driver list_windows）
#    记下 window_id，例如 4261

# 3. Agent 写入 actions.json 后，先 dry-run
python3 <skill-root>/scripts/timeline_player.py \
  --actions "$RUN/actions.json" \
  --output-dir "$RUN" \
  --dry-run

# 4. 开始单窗口录屏 + 本地动作时间轴回放（不必把目标 App 置前）
#    run_recording.py 不接受 --duration；时长由底层 record_window 从 narration.wav 自动读取
export PATH="$HOME/.local/bin:$PATH"
python3 <skill-root>/scripts/run_recording.py \
  --output-dir "$RUN" \
  --window-id 4261

# 5. screencapture 自然结束后，检查 capture/recording.report.json，再 ingest → compose
python3 <skill-root>/scripts/ingest_capture.py --output-dir "$RUN"
python3 <skill-root>/scripts/compose_video.py --output-dir "$RUN"
```

`record_window.py` 会向上取整时长（例如旁白 12.1s → 录 13s），减少尾部被截断。

## CLI 参数

### `run_recording.py`（正式录屏唯一入口）

| 参数 | 说明 |
|------|------|
| `--output-dir` | 必填。运行目录 |
| `--window-id` | 必填。目标窗口 ID |
| `--actions` | 可选。默认 `<output-dir>/actions.json` |
| `--dry-run` | 只预览动作时间轴，不录屏 |
| `--allow-foreground` | 允许 foreground 动作 |

**没有 `--duration`。** 不要传；时长由底层 `record_window.py` 从 `narration.wav` 自动推断。

### `record_window.py`（底层，通常由 run_recording 调用）

| 参数 | 说明 |
|------|------|
| `--window-id` | 必填。目标窗口 ID |
| `--duration` | 可选。秒数；省略则读 `--output-dir/narration.wav` |
| `--output-dir` | 运行目录；用于推断时长与默认输出路径 |
| `--output` | 可选。默认 `<output-dir>/capture/raw.mp4` |

## Agent 执行注意

1. **先写脚本与旁白，再录屏。**
2. 录屏前完成动作校准并写入 `actions.json`（步骤 6）。
3. 录屏时保持 `window_id` 有效（窗口不要关掉）。
4. 窗口可以在背后录；**不要**为了录屏而抢用户前台。
5. 正式录屏期间禁止逐步调用 LLM `computer_use` 推进画面。
6. 禁止用连续截图拼视频冒充本步骤。
7. 失败时检查：屏幕录制权限、window_id、旁白时长是否与 `-V` 设定一致，以及 `actions.report.json` 是否显示动作成功。

## 与失败模式的关系

- 若成片不是目标 App UI → 检查是否录错了 window_id，或权限导致录制落到错误表面。
- 若音画时长偏差过大 → 见 [failure-modes.md](failure-modes.md) 模式 4；重跑 `run_recording.py`（勿自写录屏脚本、勿在 timeline 结束后 terminate 录屏进程）。

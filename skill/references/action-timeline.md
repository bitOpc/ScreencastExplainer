# actions.json 通用 UI 动作时间轴

`actions.json` 描述正式录屏期间要执行的 UI 动作。它由 Agent 在录屏前通过少量 Computer Use 校准后写入，并由 `timeline_player.py` 直接通过 cua-driver 回放。

核心目标：**正式录制阶段不再让 LLM 每几秒调用一次 `computer_use`。**

## 顶层结构

```json
{
  "version": 1,
  "target": {
    "app_name": "Microsoft PowerPoint",
    "title_contains": "Agent 介绍"
  },
  "events": [
    {"at": 0.0, "action": "key", "key": "home"},
    {"at": 12.5, "action": "key", "key": "right"},
    {
      "at": 24.0,
      "action": "click",
      "position": {"x_ratio": 0.82, "y_ratio": 0.91}
    }
  ]
}
```

多窗口可用 `targets`：

```json
{
  "version": 1,
  "targets": {
    "slides": {"app_name": "Microsoft PowerPoint", "title_contains": "Agent 介绍"},
    "browser": {"app_name": "Google Chrome", "title_contains": "Demo"}
  },
  "events": [
    {"at": 10.0, "target": "slides", "action": "key", "key": "right"},
    {"at": 20.0, "target": "browser", "action": "scroll", "direction": "down"}
  ]
}
```

第一版正式成片仍只录一个窗口；多 target 只表示动作可打到多个窗口。

## 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | `number` | 当前固定为 `1` |
| `target` | `object` | 单目标窗口匹配条件 |
| `targets` | `object` | 多目标窗口匹配条件；与 `target` 二选一 |
| `events` | `array` | 按 `at` 秒执行的动作数组 |

### target

| 字段 | 必填 | 说明 |
|------|------|------|
| `app_name` | 是 | 来自 cua-driver `list_windows` 的应用名 |
| `title_contains` | 否 | 窗口标题包含文本，用于消除歧义 |

### event

| 字段 | 必填 | 说明 |
|------|------|------|
| `at` | 是 | 相对录屏开始的秒数，使用绝对时间轴 |
| `target` | 否 | 多 target 时的别名；默认 `default` |
| `action` | 是 | 动作名 |

## 支持动作

| action | 字段 | 场景 |
|--------|------|------|
| `wait` | `seconds`（可选） | 显式停顿；通常直接靠下一个 `at` |
| `key` | `key` | PPT 下一页、PageDown、方向键、Enter、Esc |
| `hotkey` | `keys` | `cmd+l`、`cmd+s` 等组合键 |
| `click` | `position` / `element_index` / `element_token` | 点击按钮、链接、页签 |
| `double_click` | 同 `click` | 打开项目、进入详情 |
| `right_click` | 同 `click` | 右键菜单 |
| `scroll` | `direction`、`amount`、`position`（可选） | 上下左右滚动 |
| `drag` | `from_position`、`to_position` | 拖动滑块或对象 |
| `type_text` | `text` | 搜索框、表单演示 |

## 定位策略

优先级：

1. **快捷键 / 热键**：最稳，PPT、PDF、翻页场景优先使用。
2. **窗口内相对坐标**：`x_ratio` / `y_ratio`，窗口移动不影响；窗口布局变化会影响。
3. **绝对窗口内坐标**：`x` / `y`，仅适合已固定窗口大小的场景。
4. `element_index` / `element_token` 仅适合刚校准过的短路径；跨长时间回放可能失效。

坐标示例：

```json
{"position": {"x_ratio": 0.5, "y_ratio": 0.8}}
```

## 执行命令

预览动作：

```bash
python3 <skill-root>/scripts/timeline_player.py \
  --actions ./outputs/<run-id>/actions.json \
  --output-dir ./outputs/<run-id> \
  --dry-run
```

正式录制：

```bash
python3 <skill-root>/scripts/run_recording.py \
  --output-dir ./outputs/<run-id> \
  --window-id <WINDOW_ID>
```

`run_recording.py` 会同时运行：

- `record_window.py`：单窗口连续录屏
- `timeline_player.py`：按 `actions.json` 后台回放 UI 动作

## 安全约束

- 默认 `delivery_mode = background`。
- 默认禁止 `foreground`，除非显式传 `--allow-foreground`。
- 禁止在录屏期间调用 LLM `computer_use` 做逐步操作。
- `actions.json` 只能写入用户任务相关窗口的动作。
- `type_text` 不得写入密码、密钥或隐私凭据。

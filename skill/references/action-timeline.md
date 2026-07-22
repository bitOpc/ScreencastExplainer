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
| `key` | `key` | PPT 下一页、PageDown、方向键、Enter、Esc（推荐 `Home`、`PageDown`、`End`、`Up`、`Down`，首字母大写） |
| `hotkey` | `keys` | `cmd+l`、`cmd+s` 等组合键 |
| `click` | `position` / `element_index` / `element_token` | 点击按钮、链接、页签 |
| `double_click` | 同 `click` | 打开项目、进入详情 |
| `right_click` | 同 `click` | 右键菜单 |
| `scroll` | `direction`、`amount`、`position`（可选） | 上下左右滚动 |
| `drag` | `from_position`、`to_position` | 拖动滑块或对象 |
| `type_text` | `text` | 搜索框、表单演示 |

## 定位策略

优先级（按场景调整）：

1. **快捷键 / 热键**：PPT、PDF 翻页等固定布局场景优先。
2. **click + scroll**：Obsidian、浏览器、IDE 等可滚动文档/笔记场景优先；用 click 切换页签/笔记，用 scroll 推进阅读区域。
3. **窗口内相对坐标**：`x_ratio` / `y_ratio`，窗口移动不影响；窗口布局变化会影响。
4. **绝对窗口内坐标**：`x` / `y`，仅适合已固定窗口大小的场景。
5. `element_index` / `element_token` 仅适合刚校准过的短路径；跨长时间回放可能失效。

坐标示例：

```json
{"position": {"x_ratio": 0.5, "y_ratio": 0.8}}
```

## Obsidian 多笔记 recipe（灵活模式）

适用于：同一 Vault 内多篇笔记/长文，旁白按段切换主题，画面需 click 导航 + scroll 阅读。

**模式（非固定脚本）：**

1. **校准阶段**（少量 Computer Use）：取得侧边栏笔记列表、编辑器滚动区、页签区域的相对坐标或稳定 click 目标。
2. **写入 `actions.json`**：每段旁白对应一组「必要时 click 切换笔记/页签 → scroll 推进到 `page_target`」。
3. **时间对齐**：各 event 的 `at` 来自 `segments.json` 各段 `start`（或校准后的绝对时间轴）；禁止未校准直接抄示例坐标。

**事件组合示例（坐标为 placeholder，须替换为校准值）：**

```json
{
  "version": 1,
  "target": {"app_name": "Obsidian", "title_contains": "Vault"},
  "events": [
    {"at": 0.0, "action": "click", "position": {"x_ratio": 0.12, "y_ratio": 0.22}},
    {"at": 2.0, "action": "scroll", "direction": "down", "amount": 3, "position": {"x_ratio": 0.55, "y_ratio": 0.55}},
    {"at": 45.0, "action": "click", "position": {"x_ratio": 0.12, "y_ratio": 0.35}},
    {"at": 47.0, "action": "scroll", "direction": "down", "amount": 2, "position": {"x_ratio": 0.55, "y_ratio": 0.55}}
  ]
}
```

**禁止：**

- 未校准复制上述 `x_ratio` / `y_ratio`。
- 默认用 PageDown / `cmd+o` 代替 click+scroll（Obsidian 布局因主题与插件而异，键位不稳定）。
- 录屏阶段再调用 LLM `computer_use` 逐步操作。

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

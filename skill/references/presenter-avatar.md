# 真人讲解画面（Presenter Avatar）

可选附加能力：用本地 [SadTalker](https://github.com/OpenTalker/SadTalker) 将用户**真人半身照**驱动为口型视频，以右下角圆形画中画叠到成片上。

**非目标：** 卡通 / 动漫形象、云端 API、实时流式数字人。主 skill 不依赖本能力；未安装或本片未启用时，行为与现网一致。

## 能力说明

| 项 | 说明 |
|----|------|
| 形象 | **仅真人**半身照；不支持卡通、虚拟角色 |
| 运行方式 | 本地 SadTalker（`~/.sadtalker/`，独立 venv） |
| 画中画 | 右下角圆形，宽约主画面 18%，边距 24px，叠在硬字幕之上 |
| 口型 | 跟随 `narration.wav` 分段生成，最终音轨仍为旁白 |
| 确认时机 | **安装问一次** + **每次成片再确认** |

全局配置：`~/.screencast-explainer/presenter.json`（读写见 `lib/presenter_config.py`）。

本片状态：`$RUN/avatar.json`（Agent 在用户确认后写入）。

## 安装确认剧本

在主 skill 安装完成（clone → venv → ffmpeg → 当前平台 symlink → `doctor.py` 成功）之后执行。

### 1. 询问用户

向用户说明并询问是否需要「真人讲解画面」附加能力：

1. 成片右下角会出现圆形真人讲解小窗，口型跟随旁白
2. **仅支持真人半身照**，不支持卡通
3. 完全可选；不装不影响录屏 + 旁白 + 硬字幕主流程
4. SadTalker 安装到 `~/.sadtalker/`，使用**独立 venv**，**不进入**主 skill venv（`~/.screencast-explainer-venv/`）
5. 耗时量级（粗估；成片时会按旁白实际秒数精算）：

| 硬件 | 约 10 分钟旁白的口型生成 |
|------|--------------------------|
| NVIDIA GPU（8GB+，有 CUDA） | 约 20–40 分钟 |
| 仅 CPU / Apple Silicon（无 CUDA） | **可能数小时** |

6. 半身照在**首次成片启用时**收集，安装阶段不要求上传照片

### 2. 用户选「不需要」

写入 `presenter.json`，`enabled=false`（保留其余默认字段）：

```bash
PYTHONPATH=~/.screencast-explainer/skill/scripts \
  python3 -c '
from lib.presenter_config import default_presenter_config, save_presenter_config
cfg = default_presenter_config()
cfg["enabled"] = False
save_presenter_config(cfg)
'
```

主 skill 照常可用；`doctor.py` **不**把 SadTalker 当必检项。

### 3. 用户选「需要」

1. 检测 CUDA：`nvidia-smi` 可用且返回成功 → `has_cuda=true`；否则 `has_cuda=false`
2. **若无 CUDA**：必须单独告知「可能数小时」，并要求用户明确回复（示例话术见下）后才可继续
3. 用户确认后执行安装（**必须**带 `--yes`；可先 `--dry-run` 预览）：

```bash
cd ~/.screencast-explainer
bash scripts/install_presenter.sh --yes
# 预览：bash scripts/install_presenter.sh --dry-run --yes
```

`install_presenter.sh` **拒绝**无 `--yes` 的静默安装。安装完成后 `presenter.json` 中 `enabled=true`、`installed=true`，并记录 `sadtalker_root`、`has_cuda`。

### 无 CUDA 确认话术（安装时）

Agent 必须让用户明确知晓并接受较慢速度，例如：

> 未检测到 NVIDIA CUDA，SadTalker 将使用 CPU。生成约 10 分钟旁白对应的口型视频**可能数小时**。若仍要安装，请回复「我已知晓并接受较慢速度」。

收到明确肯定答复后，才可运行 `install_presenter.sh --yes`。

## 成片三步确认

**触发条件：** `build_narration.py` 完成后（已有 `narration.wav` 与分段时长），且 `presenter.json` 中 `enabled=true` 且 `installed=true`。否则跳过本节，直接进入 UI 校准与录屏。

### 步骤 1：本片是否启用？

问用户：**本片是否要加真人讲解画面？**

- **否** → 不写 `$RUN/avatar.json`，或设 `use_presenter=false`；后续 `compose_video.py` 不叠加 avatar
- **是** → 进入步骤 2

### 步骤 2：告知本片预估耗时并确认

读取旁白实际秒数（`ffprobe` 或 `narration.wav` 时长），结合 `presenter.json` 的 `has_cuda`，用与 `estimate_avatar_minutes` **一致**的公式告知用户：

**有 CUDA（`has_cuda=true`，默认 fast 档）：**

- 预估分钟下限 = 旁白秒数 × 1.5 / 60
- 预估分钟上限 = 旁白秒数 × 3 / 60
- 告知示例：`预估约 15–30 分钟`（10 分钟旁白即 600 秒）
- 生成耗时约为旁白的约 1.5–3 倍（`quality` 档更接近旧的 2–4 倍）

Agent 可调用：

```bash
PYTHONPATH=<skill-root>/scripts python3 -c "
from lib.presenter_config import load_presenter_config, estimate_avatar_minutes
import subprocess, json
cfg = load_presenter_config()
dur = float(subprocess.check_output([
    'ffprobe','-v','error','-show_entries','format=duration',
    '-of','csv=p=0','<RUN>/narration.wav'
], text=True).strip())
print(json.dumps(estimate_avatar_minutes(dur, has_cuda=cfg['has_cuda']), ensure_ascii=False))
"
```

**无 CUDA（`has_cuda=false`）：**

- 明确写「**可能数小时**」（`needs_slow_confirm=true`）
- 须用户再次明确确认（如「继续生成」）后才可跑 `build_avatar.py`

未告知耗时并获用户确认 → **禁止**开始生成。

### 步骤 3：半身照 + 构图选择

| 情况 | Agent 动作 |
|------|------------|
| `avatar_image` 已配置且文件存在 | 展示路径，问沿用 / 更换 |
| `null` 或文件缺失 | **必须**收集本地 JPG/PNG，复制到默认路径并写回配置 |

**照片要求（真人 only）：**

- 真人正面照，脸部清晰、光线均匀（可含半身/全身，后续再裁构图）
- 建议单边分辨率 ≥ 512px
- 格式：`.jpg` / `.jpeg` / `.png`
- **禁止**卡通、插画、AI 虚拟脸、占位图

**默认落盘路径：** `~/.screencast-explainer/avatars/default.png`

复制并更新配置后，**必须**生成构图预览并让用户选择：

```bash
PYTHONPATH=<skill-root>/scripts python3 -c "
from pathlib import Path
from lib.presenter_config import install_avatar_image, load_presenter_config, save_presenter_config
src = Path('<用户提供的照片路径>')
dest = install_avatar_image(src)
cfg = load_presenter_config()
cfg['avatar_image'] = str(dest)
save_presenter_config(cfg)
print(dest)
"

# 检脸并导出 head / medium / full 预览
PYTHONPATH=<skill-root>/scripts \
  python3 <skill-root>/scripts/prepare_avatar_framing.py \
    --image ~/.screencast-explainer/avatars/default.png \
    --output-dir "$RUN/avatar_framing"
```

Agent 向用户展示 `$RUN/avatar_framing/{head,medium,full}.png` 三条路径与说明，请用户选择构图：

| 模式 | 说明 | SadTalker |
|------|------|-----------|
| `head`（默认推荐小窗） | 头部特写 | `crop` + **可动**（`still=false`） |
| `medium` | 中景（肩+背景） | `full` + **锁姿**（`still=true`） |
| `full` | 全景（尽量全身） | `full` + **锁姿**（`still=true`） |

用户选定后：

```bash
PYTHONPATH=<skill-root>/scripts \
  python3 <skill-root>/scripts/prepare_avatar_framing.py \
    --output-dir "$RUN/avatar_framing" \
    --select head   # 或 medium / full
```

将 `selection.json` 内容写入 `$RUN/avatar.json`（示例）：

```json
{
  "use_presenter": true,
  "framing_mode": "head",
  "source_image": "/path/to/$RUN/avatar_framing/chosen.png",
  "source_original": "/path/to/$RUN/avatar_framing/original.png",
  "sadtalker": {
    "still": false,
    "preprocess": "crop"
  },
  "estimated_seconds": 613,
  "user_confirmed_slow": true
}
```

**硬规则：** 未完成构图选择、未写入 `framing_mode` + `source_image`（chosen 图）→ **禁止**调用 `build_avatar.py`。

`user_confirmed_slow`：无 CUDA 时为 `true`；有 CUDA 时可省略或设为 `false`。

## SadTalker 性能档位（`profile`）与构图（`framing_mode`）

写入 `~/.screencast-explainer/presenter.json` 的 `profile` 字段控制**分辨率/batch**。本片 `avatar.json` 的 `framing_mode` 优先决定 **`still` / `preprocess`**。

| profile | size | batch_size | 说明 |
|---------|------|------------|------|
| **fast**（默认） | 256 | 4（无 CUDA 时钳到 ≤2） | 最快；小窗够用 |
| **balanced** | 256 | 4（≤2） | 同 256，便于覆盖 |
| **quality** | 512 | 2 | 更清晰、更慢 |

| framing_mode | preprocess | still |
|--------------|------------|-------|
| `head` | crop | false |
| `medium` / `full` | full | true |

说明：

- SadTalker **固定 25fps**，不要指望改 15fps 加速（会伤口型）
- **不要**默认开 `--enhancer gfpgan`（很慢）
- `batch_size` 由 `build_avatar.py` 传给 `inference.py`；显存不足时改为 `2` 或改用 `quality`
- 中景/全景**必须** `still=true`，否则易出现「头动身子不动」

示例（切到更清晰档）：

```bash
PYTHONPATH=<skill-root>/scripts python3 -c "
from lib.presenter_config import load_presenter_config, save_presenter_config
cfg = load_presenter_config()
cfg['profile'] = 'quality'
save_presenter_config(cfg)
"
```

## 流水线顺序与命令

v1 固定串行：`build_avatar` 只依赖旁白，**在录屏之前**完成。

```
doctor → init_run → [script + segments]
→ build_narration
→（本片三步确认 + 可选 build_avatar）
→ [校准 actions.json]
→ run_recording → ingest_capture → compose_video → build_cover
```

启用本片 avatar 时：

```bash
python3 <skill-root>/scripts/build_avatar.py --output-dir "$RUN"

python3 <skill-root>/scripts/run_recording.py \
  --output-dir "$RUN" \
  --window-id <WINDOW_ID>

python3 <skill-root>/scripts/ingest_capture.py --output-dir "$RUN"

python3 <skill-root>/scripts/compose_video.py --output-dir "$RUN"
# 或显式：--with-avatar / --no-avatar
```

- `build_avatar.py` 输出无音轨 `video/avatar.mp4` 与 `video/avatar.report.json`
- `compose_video.py` 默认根据 `$RUN/avatar.json` 与 `video/avatar.mp4` 自动决定是否叠加；`--with-avatar` 强制叠加，`--no-avatar` 强制跳过

用户取消或 avatar 生成失败时，仍可用 `--no-avatar` 交付无角色的 `final.mp4`。

## 硬规则

### 安装

1. **禁止**默认或静默安装 SadTalker；`install_presenter.sh` 必须用户确认后以 `--yes` 调用
2. **禁止**跳过无 CUDA 的单独确认
3. 用户选「不需要」时只写 `enabled=false`，主流程不受影响
4. **禁止**在安装阶段替用户默认开启 `enabled=true`

### 成片

1. 未获「本片启用」确认 → **禁止**调用 SadTalker / `build_avatar.py`
2. 未告知耗时并获确认 → **禁止**开始生成
3. 无合格半身照 → **禁止**生成；**禁止**用占位图
4. **禁止**因用户未确认而擅自叠加 avatar
5. avatar 失败时：报告原因；经用户同意后可 `--no-avatar` 继续合成

### 与主流程

1. `doctor.py` 对 presenter 为**可选报告**（`presenter_enabled` / `presenter_installed` / `presenter_has_cuda` / `presenter_avatar`）；缺失不阻断主流程
2. 未启用 presenter 时，`compose_video.py` 行为与现网一致

## 相关路径速查

| 路径 | 用途 |
|------|------|
| `~/.screencast-explainer/presenter.json` | 全局开关、SadTalker 根目录、CUDA 探测、默认半身照 |
| `~/.screencast-explainer/avatars/default.png` | 默认半身照落盘 |
| `~/.sadtalker/` | SadTalker 源码、venv、权重（`SADTALKER_ROOT` 可覆盖） |
| `$RUN/avatar.json` | 本片是否启用、构图模式、chosen 源图、预估秒数、慢速确认 |
| `$RUN/avatar_framing/` | head/medium/full 预览、`framing_options.json`、`chosen.png` |
| `$RUN/video/avatar.mp4` | 本片无音轨口型视频 |
| `$RUN/video/avatar.report.json` | 分段生成报告 |

安装与更新 SadTalker 见仓库 `docs/install.md`、`docs/update.md`。

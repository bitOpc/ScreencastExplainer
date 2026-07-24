# 可选附加能力：真人讲解画面（Presenter Avatar）

**Date:** 2026-07-23  
**Status:** Approved (brainstorming)  
**Approach:** Agent 对话驱动（方案 1）  
**Scope:** 仅真人半身照；本地 SadTalker；不支持卡通

---

## 1. Summary

在 Screencast Explainer 主流程（录屏 + 旁白 + 硬字幕）之上，增加**可选**附加能力：用本地 [SadTalker](https://github.com/OpenTalker/SadTalker) 将用户半身照驱动为口型视频，再以右下角圆形画中画叠到成片上。

| 决策 | 选择 |
|------|------|
| 运行方式 | **仅本地** SadTalker（独立目录与 venv） |
| 确认时机 | 安装问一次 + **每次成片再确认** |
| 半身照 | **首次启用时**收集，之后复用可换 |
| 无 NVIDIA CUDA | **允许安装与使用**，但强警告 + 用户明确确认 |
| 编排方式 | Agent 按 `docs/install.md` / `SKILL.md` 剧本执行；不静默安装 |

主 skill 不依赖本能力；未安装或本片未启用时，行为与现网一致。

---

## 2. 安装时流程

在主 skill 安装完成（clone → venv → ffmpeg → 当前平台 symlink → doctor）之后追加：

```
主 skill 安装完成
        ↓
Agent 询问：是否需要「真人讲解画面」附加能力？
   ├─ 否 → presenter.enabled=false，结束
   └─ 是 → 检测 GPU →（无 CUDA 则强警告）→ 用户确认
            → install_presenter.sh → presenter.installed=true
            → 提示：半身照在首次成片启用时收集
```

### Agent 安装时必须说明

1. 右下角圆形真人讲解小窗，口型跟随旁白；**仅真人半身照**，不支持卡通  
2. 可选；不装不影响主流程  
3. 本地安装到 `~/.sadtalker/`，独立 venv，**不进入**主 skill venv  
4. 耗时量级（粗估；成片时再按旁白精算）：

| 硬件 | 约 10 分钟旁白的口型生成 |
|------|--------------------------|
| NVIDIA GPU（8GB+） | 约 20–40 分钟 |
| 仅 CPU / Apple Silicon | 可能数小时 |

5. 无 CUDA：须用户明确回复（如「我已知晓并接受较慢速度」）后才可安装  

### 硬规则（安装）

- **禁止**默认静默安装 SadTalker  
- **禁止**跳过「无 GPU」确认  
- 用户选「不需要」时主 skill 照常可用；`doctor.py` **不**把 SadTalker 当必检项  

---

## 3. 全局配置

路径：`~/.screencast-explainer/presenter.json`

```json
{
  "enabled": false,
  "installed": false,
  "sadtalker_root": "~/.sadtalker",
  "has_cuda": false,
  "avatar_image": null,
  "layout": {
    "position": "bottom-right",
    "width_ratio": 0.18,
    "margin_px": 24,
    "shape": "circle"
  },
  "profile": "fast",
  "sadtalker": {
    "still": true,
    "preprocess": "crop",
    "face_model_resolution": 256,
    "batch_size": 4
  }
}
```

| 字段 | 含义 |
|------|------|
| `enabled` | 用户是否选择安装该附加能力 |
| `installed` | SadTalker 是否实际装好 |
| `avatar_image` | 默认半身照路径；首次使用前为 `null` |
| `has_cuda` | 安装时探测结果，供耗时估算 |

默认角色照落盘：`~/.screencast-explainer/avatars/default.png`（首次收集时复制）。

---

## 4. 每次成片确认

**触发：** `build_narration.py` 完成后（已有 `narration.wav` 与分段时长），且 `enabled=true` 且 `installed=true`。否则跳过。

### 三步必问

1. **本片是否启用真人讲解？** 否 → 本片无 avatar，正常 compose。  
2. **告知本片预估耗时**（按旁白实际秒数），用户确认「继续」后才可跑 `build_avatar.py`。  
3. **半身照：**  
   - 已有且文件存在 → 展示路径，问沿用 / 更换  
   - `null` 或缺失 → **必须**收集本地 JPG/PNG（真人正面、脸清晰、建议上半身、单边 ≥ 512px），复制到 `avatars/default.png` 并写回配置  

### 耗时估算（Agent 照搬）

| 条件 | 告知方式 |
|------|----------|
| `has_cuda=true` | 预估分钟 ≈ 旁白秒数 × (2～4) / 60（实时率约 0.25–0.5×） |
| `has_cuda=false` | 明确写「可能数小时」，并再次要求确认 |

### 本片状态文件

`$RUN/avatar.json`：

```json
{
  "use_presenter": true,
  "source_image": "~/.screencast-explainer/avatars/default.png",
  "estimated_seconds": 613,
  "user_confirmed_slow": true
}
```

### 硬规则（成片）

- 未获「本片启用」确认 → **禁止**调用 SadTalker  
- 未告知耗时并获确认 → **禁止**开始生成  
- 无半身照 → **禁止**生成；不可用占位图  
- 用户取消 → 跳过 avatar，仍可输出无角色的 `final.mp4`  

---

## 5. 流水线接入

### 顺序（v1 固定串行）

```
narrate →（本片确认 / 半身照）→ build_avatar → record → ingest → compose（± PiP）→ cover
```

`build_avatar` 只依赖旁白时间轴，不依赖录屏；v1 不并行，降低 Agent 编排复杂度。

### 新增 / 扩展

| 产物 | 职责 |
|------|------|
| `scripts/install_presenter.sh` | 克隆 SadTalker、独立 venv、下载权重；更新 `presenter.json` |
| `skill/scripts/build_avatar.py` | 读 `$RUN/avatar.json` + 分段 WAV → 本地 SadTalker → `video/avatar.mp4` |
| `compose_video.py` | 存在 avatar 且本片启用 → 圆形右下角 overlay；否则不变 |
| `doctor.py` | **可选**报告 `presenter`（installed / has_cuda / avatar_image）；缺失不阻断主流程 |

### build_avatar

1. 按 `workaudio/edge_clips/clip_*.wav` **分段**调用 SadTalker（默认 `profile=fast`：`--still --preprocess crop --size 256 --batch_size 4`；无 CUDA 时 batch≤2）  
2. 段间 gap 用静止帧对齐 `narration.wav`  
3. 输出 **无音轨** `video/avatar.mp4`（最终音轨仍为 `narration.wav`）  
4. 写 `video/avatar.report.json`（每段耗时、成败）  
5. 单段失败：报告；允许只重跑该段；不静默跳过  

### compose PiP

- 右下角；宽 ≈ 主画面 18%；边距 24px；圆形遮罩  
- v1：avatar 叠在**字幕之上**（小窗不被字幕挡住）  
- 实现：ffmpeg scale → 圆形 alpha → overlay  

### 失败降级

| 情况 | 行为 |
|------|------|
| SadTalker 崩溃 / 超时 | 提示；可选「不要角色继续合成」 |
| `avatar.mp4` 缺失 | compose 按无角色处理（除非用户强制要求必须有角色） |
| 主流程 doctor 失败 | 与现网一致，阻断 |

---

## 6. 文档改动

| 文件 | 改动 |
|------|------|
| `docs/install.md` | 追加可选 Presenter 步骤与确认剧本 |
| `docs/update.md` | 可选：如何更新 / 卸载 SadTalker |
| `skill/SKILL.md` | 硬规则：确认、耗时、半身照、禁止静默 |
| `skill/references/presenter-avatar.md` | 参数、估算公式、照片要求、SadTalker CLI |
| `README.md` / `README.zh-CN.md` | 一句说明可选真人讲解附加能力 |

---

## 7. 非目标（本规格不做）

- 卡通 / 动漫形象  
- 云端 API（Replicate / fal / 腾讯 IVH 等）  
- 实时流式数字人  
- 把 PyTorch / SadTalker 装进主 skill venv  
- 安装时强制收集半身照  

---

## 8. 成功标准

1. 用户选「不需要」时，安装与成片与现网无差异  
2. 用户选「需要」时，仅在确认后安装本地 SadTalker；无 CUDA 须二次确认  
3. 每次成片启用前：告知耗时并获确认；无照则收集半身照  
4. 启用后成片右下角出现圆形真人讲解画面，口型与旁白对齐  
5. 取消或 avatar 失败时，仍可交付无角色的硬字幕成片  

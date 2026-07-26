"""圆形 avatar 画中画 ffmpeg filter_complex 构建。"""

from pathlib import Path

# SadTalker 输出固定 25fps；合成时不低于此值，避免低帧率录屏把口型抽稀。
DEFAULT_MIN_PIP_FPS = 25


def resolve_pip_output_fps(
    main_fps: float | None,
    *,
    min_fps: int = DEFAULT_MIN_PIP_FPS,
) -> int:
    """PiP 合成输出帧率：至少 min_fps，且不低于主画面有效帧率。"""
    if main_fps is None or main_fps <= 0:
        return min_fps
    return max(min_fps, int(round(main_fps)))


def _format_ass_filter(path: Path) -> str:
    """生成 ffmpeg ass 滤镜参数字符串，路径含特殊字符时用单引号转义。"""
    path_str = path.as_posix()
    if any(ch in path_str for ch in " ':,;[]"):
        escaped = path_str.replace("'", "'\\''")
        return f"ass=filename='{escaped}'"
    return f"ass=filename={path_str}"


def build_pip_filter_complex(
    *,
    captions_ass: Path,
    size_ratio: float = 0.24,
    margin_px: int = 24,
    fps: int = DEFAULT_MIN_PIP_FPS,
) -> str:
    """构建圆形右下角 PiP 的 filter_complex，输出标签 [vout]。

    主画面与 avatar 均先统一到 ``fps``，再缩放/圆形遮罩/叠加，避免主画面
    低帧率把口型拖成卡顿。
    """
    if fps < 1:
        raise ValueError(f"fps 必须 >= 1，收到: {fps}")
    ass_filter = _format_ass_filter(captions_ass)
    # scale2ref 的表达式应参考主画面高度（rh），不能直接用 avatar 源尺寸做缩放。
    pip_size = f"trunc(rh*{size_ratio}/2)*2"
    return (
        f"[0:v]{ass_filter},fps={fps}[base];"
        f"[1:v]fps={fps}[pip_src];"
        f"[pip_src][base]scale2ref=w={pip_size}:h={pip_size}[pip_scaled][base_ref];"
        f"[pip_scaled]format=rgba,"
        f"geq=lum='p(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),min(W,H)/2),255,0)'[pip];"
        f"[base_ref][pip]overlay=main_w-overlay_w-{margin_px}:main_h-overlay_h-{margin_px}[vout]"
    )

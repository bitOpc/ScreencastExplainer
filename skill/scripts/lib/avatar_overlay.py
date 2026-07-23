"""圆形 avatar 画中画 ffmpeg filter_complex 构建。"""

from pathlib import Path


def _format_ass_filter(path: Path) -> str:
    """生成 ffmpeg ass 滤镜参数字符串，路径含特殊字符时用单引号转义。"""
    path_str = path.as_posix()
    if any(ch in path_str for ch in " ':,;[]"):
        escaped = path_str.replace("'", "'\\''")
        return f"ass='{escaped}'"
    return f"ass={path_str}"


def build_pip_filter_complex(
    *,
    captions_ass: Path,
    width_ratio: float = 0.18,
    margin_px: int = 24,
) -> str:
    """构建圆形右下角 PiP 的 filter_complex，输出标签 [vout]。"""
    ass_filter = _format_ass_filter(captions_ass)
    return (
        f"[0:v]{ass_filter}[base];"
        f"[1:v]scale=iw*{width_ratio}:-1,format=rgba,"
        f"geq=lum='p(X,Y)':a='if(lte(hypot(X-W/2,Y-H/2),min(W,H)/2),255,0)'[pip];"
        f"[base][pip]overlay=main_w-overlay_w-{margin_px}:main_h-overlay_h-{margin_px}[vout]"
    )

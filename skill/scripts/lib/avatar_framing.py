"""根据真人照片检脸并导出 head/medium/full 方形构图预览。"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from lib.presenter_config import FRAMING_MODES, framing_sadtalker_params

# 相对脸宽的方形边长倍数：head 紧、medium 含肩、full 尽量大
_FACE_SCALE = {
    "head": 2.4,
    "medium": 4.2,
    "full": 6.5,
}


@dataclass(frozen=True)
class FaceBox:
    left: int
    top: int
    width: int
    height: int

    @property
    def cx(self) -> float:
        return self.left + self.width / 2

    @property
    def cy(self) -> float:
        return self.top + self.height / 2


def detect_face_box(image: Image.Image) -> FaceBox | None:
    """OpenCV Haar 检脸；失败返回 None。"""
    try:
        import cv2  # type: ignore
        import numpy as np
    except ImportError:
        return None

    if not hasattr(cv2, "CascadeClassifier") or not hasattr(cv2, "data"):
        return None

    try:
        rgb = image.convert("RGB")
        arr = np.array(rgb)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        detector = cv2.CascadeClassifier(str(cascade_path))
        faces = detector.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(48, 48)
        )
    except Exception:
        return None

    if faces is None or len(faces) == 0:
        return None
    # 取最大脸
    x, y, w, h = max(faces, key=lambda f: int(f[2]) * int(f[3]))
    return FaceBox(left=int(x), top=int(y), width=int(w), height=int(h))


def heuristic_face_box(image: Image.Image) -> FaceBox:
    """无检脸时：假定人脸在画面上半部居中。"""
    width, height = image.size
    face_w = max(64, int(min(width, height) * 0.28))
    face_h = face_w
    left = (width - face_w) // 2
    top = max(0, int(height * 0.12))
    if top + face_h > height:
        top = max(0, height - face_h)
    return FaceBox(left=left, top=top, width=face_w, height=face_h)


def square_crop_around_face(
    image: Image.Image,
    face: FaceBox,
    *,
    scale: float,
    bias_down: float = 0.15,
) -> Image.Image:
    """以脸为中心取方形裁切；bias_down>0 时略向下偏以纳入肩部。"""
    width, height = image.size
    side = int(max(face.width, face.height) * scale)
    side = max(64, min(side, width, height))
    cx = face.cx
    cy = face.cy + face.height * bias_down
    left = int(round(cx - side / 2))
    top = int(round(cy - side / 2))
    left = max(0, min(left, width - side))
    top = max(0, min(top, height - side))
    return image.crop((left, top, left + side, top + side))


def build_framing_crops(
    image: Image.Image, face: FaceBox
) -> dict[str, Image.Image]:
    """生成三种构图的方形图。"""
    return {
        "head": square_crop_around_face(
            image, face, scale=_FACE_SCALE["head"], bias_down=0.05
        ),
        "medium": square_crop_around_face(
            image, face, scale=_FACE_SCALE["medium"], bias_down=0.35
        ),
        "full": square_crop_around_face(
            image, face, scale=_FACE_SCALE["full"], bias_down=0.55
        ),
    }


def prepare_framing_previews(
    source_image: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """
    从原图导出 head/medium/full 预览，并写 framing_options.json。

    返回写入的选项摘要（含路径与 SadTalker 参数提示）。
    """
    source_image = source_image.expanduser().resolve()
    if not source_image.is_file():
        raise FileNotFoundError(f"找不到源图片: {source_image}")

    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    original = Image.open(source_image).convert("RGB")
    original_path = output_dir / f"original{source_image.suffix.lower() or '.png'}"
    if original_path.suffix not in {".jpg", ".jpeg", ".png"}:
        original_path = output_dir / "original.png"
    if source_image.resolve() != original_path.resolve():
        shutil.copy2(source_image, original_path)
    else:
        original.save(original_path)

    detected = detect_face_box(original)
    face_detected = detected is not None
    face = detected or heuristic_face_box(original)
    crops = build_framing_crops(original, face)

    options: dict[str, Any] = {}
    for mode, crop in crops.items():
        out_path = output_dir / f"{mode}.png"
        crop.save(out_path, format="PNG")
        meta = FRAMING_MODES[mode]
        options[mode] = {
            "label": meta["label"],
            "description": meta["description"],
            "path": str(out_path),
            "sadtalker": framing_sadtalker_params(mode),
        }

    payload = {
        "source_original": str(original_path),
        "face_detected": face_detected,
        "face_box": {
            "left": face.left,
            "top": face.top,
            "width": face.width,
            "height": face.height,
        },
        "recommended": "head",
        "options": options,
    }
    options_path = output_dir / "framing_options.json"
    options_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def select_framing_mode(output_dir: Path, framing_mode: str) -> dict[str, Any]:
    """确认构图：复制为 chosen.png，并返回供 avatar.json 使用的字段。"""
    if framing_mode not in FRAMING_MODES:
        raise ValueError(
            f"未知 framing_mode: {framing_mode}；可选: {', '.join(FRAMING_MODES)}"
        )
    output_dir = output_dir.expanduser().resolve()
    options_path = output_dir / "framing_options.json"
    if not options_path.is_file():
        raise FileNotFoundError(f"缺少 {options_path}，请先生成预览")

    payload = json.loads(options_path.read_text(encoding="utf-8"))
    option = payload["options"][framing_mode]
    preview = Path(option["path"])
    if not preview.is_file():
        raise FileNotFoundError(f"预览图不存在: {preview}")

    chosen = output_dir / "chosen.png"
    shutil.copy2(preview, chosen)

    selection = {
        "framing_mode": framing_mode,
        "source_image": str(chosen),
        "source_original": payload.get("source_original"),
        "sadtalker": dict(option["sadtalker"]),
        "face_detected": bool(payload.get("face_detected")),
    }
    selection_path = output_dir / "selection.json"
    selection_path.write_text(
        json.dumps(selection, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return selection

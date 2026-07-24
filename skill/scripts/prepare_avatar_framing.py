#!/usr/bin/env python3
"""生成或确认 Avatar 构图预览（head / medium / full）。"""

import argparse
import json
from pathlib import Path

from lib.avatar_framing import prepare_framing_previews, select_framing_mode
from lib.presenter_config import FRAMING_MODES


def main() -> None:
    parser = argparse.ArgumentParser(
        description="检脸并导出头部/中景/全景预览，或确认某构图为 chosen.png"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="输出目录（建议 $RUN/avatar_framing）",
    )
    parser.add_argument(
        "--image",
        type=Path,
        help="源真人照片（生成预览时必填）",
    )
    parser.add_argument(
        "--select",
        choices=sorted(FRAMING_MODES.keys()),
        help="确认构图模式：复制为 chosen.png 并写 selection.json",
    )
    args = parser.parse_args()

    if args.select:
        selection = select_framing_mode(args.output_dir, args.select)
        print(json.dumps(selection, ensure_ascii=False, indent=2))
        return

    if args.image is None:
        parser.error("生成预览时必须提供 --image")

    payload = prepare_framing_previews(args.image, args.output_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload.get("face_detected"):
        print(
            "警告: 未检到人脸，已用启发式裁切；预览可能不准。",
            flush=True,
        )


if __name__ == "__main__":
    main()

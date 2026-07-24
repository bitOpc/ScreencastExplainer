"""avatar_framing / framing_mode 相关测试。"""

import json
from pathlib import Path

from PIL import Image

from lib.avatar_framing import (
    FaceBox,
    build_framing_crops,
    heuristic_face_box,
    prepare_framing_previews,
    select_framing_mode,
    square_crop_around_face,
)
from lib.presenter_config import framing_sadtalker_params, resolve_sadtalker_settings
from build_avatar import _presenter_config


def test_framing_sadtalker_params_head_allows_motion():
    params = framing_sadtalker_params("head")
    assert params["still"] is False
    assert params["preprocess"] == "crop"


def test_framing_sadtalker_params_medium_locks_pose():
    params = framing_sadtalker_params("medium")
    assert params["still"] is True
    assert params["preprocess"] == "full"


def test_resolve_framing_overrides_profile_still_preprocess():
    settings = resolve_sadtalker_settings(
        {
            "profile": "fast",
            "has_cuda": True,
            "framing_mode": "medium",
            "sadtalker": {},
        }
    )
    assert settings["still"] is True
    assert settings["preprocess"] == "full"
    assert settings["face_model_resolution"] == 256


def test_avatar_json_sadtalker_wins_over_framing():
    config = _presenter_config(
        {"profile": "fast", "has_cuda": True},
        avatar={
            "framing_mode": "head",
            "sadtalker": {"still": True, "preprocess": "full"},
        },
    )
    assert config["sadtalker"]["still"] is True
    assert config["sadtalker"]["preprocess"] == "full"


def test_presenter_config_applies_head_framing_from_avatar():
    config = _presenter_config(
        {"profile": "fast", "has_cuda": True},
        avatar={"framing_mode": "head"},
    )
    assert config["framing_mode"] == "head"
    assert config["sadtalker"]["still"] is False
    assert config["sadtalker"]["preprocess"] == "crop"


def test_square_crop_stays_inside_image():
    image = Image.new("RGB", (400, 300), color=(10, 20, 30))
    face = FaceBox(left=150, top=40, width=80, height=80)
    crop = square_crop_around_face(image, face, scale=3.0, bias_down=0.2)
    assert crop.size[0] == crop.size[1]
    assert crop.size[0] <= 300


def test_build_framing_crops_three_modes():
    image = Image.new("RGB", (640, 480), color=(40, 40, 40))
    face = heuristic_face_box(image)
    crops = build_framing_crops(image, face)
    assert set(crops) == {"head", "medium", "full"}
    for crop in crops.values():
        assert crop.size[0] == crop.size[1]


def test_prepare_and_select_framing(tmp_path):
    src = tmp_path / "photo.png"
    Image.new("RGB", (512, 512), color=(90, 100, 110)).save(src)
    out_dir = tmp_path / "avatar_framing"

    payload = prepare_framing_previews(src, out_dir)
    assert (out_dir / "head.png").is_file()
    assert (out_dir / "medium.png").is_file()
    assert (out_dir / "full.png").is_file()
    assert (out_dir / "framing_options.json").is_file()
    assert payload["recommended"] == "head"

    selection = select_framing_mode(out_dir, "medium")
    assert selection["framing_mode"] == "medium"
    assert Path(selection["source_image"]).name == "chosen.png"
    assert Path(selection["source_image"]).is_file()
    assert selection["sadtalker"]["still"] is True
    assert selection["sadtalker"]["preprocess"] == "full"
    saved = json.loads((out_dir / "selection.json").read_text(encoding="utf-8"))
    assert saved["framing_mode"] == "medium"

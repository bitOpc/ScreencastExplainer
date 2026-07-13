"""ingest_capture.py 单元测试。"""

import pytest

from ingest_capture import validate_av_duration


def test_validate_av_duration_within_tolerance():
    validate_av_duration(video_duration=60.0, audio_duration=60.3, tolerance=0.5)


def test_validate_av_duration_raises():
    with pytest.raises(ValueError, match="音画时长偏差"):
        validate_av_duration(video_duration=50.0, audio_duration=60.0, tolerance=0.5)

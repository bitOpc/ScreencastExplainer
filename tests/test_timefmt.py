from lib.timefmt import ass_time, parse_srt_time, srt_time


def test_srt_roundtrip():
    assert srt_time(65.5) == "00:01:05,500"
    assert parse_srt_time("00:01:05,500") == 65.5


def test_ass_time():
    assert ass_time(65.5) == "0:01:05.50"

import json

from lib.action_timeline import ActionEvent, ActionTimeline, TargetRef
from timeline_player import play_timeline


class FakeClock:
    def __init__(self):
        self.now_value = 0.0
        self.sleeps = []

    def now(self):
        return self.now_value

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now_value += seconds


class FakeClient:
    def __init__(self):
        self.calls = []

    def list_windows(self):
        return [
            {
                "pid": 11,
                "window_id": 22,
                "app_name": "Keynote",
                "title": "Demo Deck",
                "bounds": [100, 100, 800, 600],
            }
        ]

    def call(self, tool, args):
        self.calls.append((tool, args))
        return {"ok": True}


def test_play_timeline_resolves_target_and_executes_by_absolute_time():
    timeline = ActionTimeline(
        version=1,
        targets={"slides": TargetRef(app_name="Keynote", title_contains="Demo")},
        events=[
            ActionEvent(at=1.5, action="key", target="slides", payload={"key": "right"}),
            ActionEvent(
                at=3.0,
                action="click",
                target="slides",
                payload={"position": {"x_ratio": 0.5, "y_ratio": 0.5}},
            ),
        ],
    )
    client = FakeClient()
    clock = FakeClock()

    report = play_timeline(timeline, client=client, clock=clock)

    assert clock.sleeps == [1.5, 1.5]
    assert [call[0] for call in client.calls] == ["press_key", "click"]
    assert client.calls[1][1]["x"] == 400
    assert client.calls[1][1]["y"] == 300
    assert report["events_executed"] == 2


def test_play_timeline_dry_run_does_not_call_driver():
    timeline = ActionTimeline(
        version=1,
        targets={"default": TargetRef(app_name="Keynote")},
        events=[
            ActionEvent(at=0, action="key", target="default", payload={"key": "right"}),
        ],
    )
    client = FakeClient()

    report = play_timeline(timeline, client=client, dry_run=True)

    assert client.calls == []
    assert report["events_executed"] == 0
    assert report["events_planned"] == 1


def test_cli_report_is_json_serializable():
    timeline = ActionTimeline(
        version=1,
        targets={"default": TargetRef(app_name="Keynote")},
        events=[
            ActionEvent(at=0, action="wait", target="default", payload={}),
        ],
    )

    report = play_timeline(timeline, client=FakeClient(), dry_run=True)

    json.dumps(report, ensure_ascii=False)

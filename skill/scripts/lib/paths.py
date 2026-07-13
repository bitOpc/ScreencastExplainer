"""运行目录路径解析。"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunPaths:
    root: Path

    @property
    def run_json(self) -> Path:
        return self.root / "run.json"

    @property
    def segments_json(self) -> Path:
        return self.root / "segments.json"

    @property
    def script_md(self) -> Path:
        return self.root / "script.md"

    @property
    def narration_wav(self) -> Path:
        return self.root / "narration.wav"

    @property
    def captions_srt(self) -> Path:
        return self.root / "captions.srt"

    @property
    def captions_ass(self) -> Path:
        return self.root / "captions.ass"

    @property
    def capture_dir(self) -> Path:
        return self.root / "capture"

    @property
    def raw_mp4(self) -> Path:
        return self.capture_dir / "raw.mp4"

    @property
    def video_dir(self) -> Path:
        return self.root / "video"

    @property
    def normalized_mp4(self) -> Path:
        return self.video_dir / "normalized.mp4"

    @property
    def final_mp4(self) -> Path:
        return self.video_dir / "final.mp4"

    @property
    def work_audio_dir(self) -> Path:
        return self.root / "workaudio"

    def ensure_dirs(self) -> None:
        """创建运行所需子目录。"""
        self.capture_dir.mkdir(parents=True, exist_ok=True)
        self.video_dir.mkdir(parents=True, exist_ok=True)
        self.work_audio_dir.mkdir(parents=True, exist_ok=True)

#!/usr/bin/env python3
"""Edge TTS 配音与字幕生成。"""

import argparse
import asyncio
import wave
from pathlib import Path

import edge_tts

from lib.ffmpeg_util import run_ffmpeg
from lib.paths import RunPaths
from lib.run_state import load_segments, save_segments, update_run_status
from lib.subtitles import write_subtitles
from lib.timefmt import parse_srt_time, srt_time

DEFAULT_VOICE_ID = "zh-CN-YunxiNeural"
DEFAULT_VOICE_RATE = "-3%"
DEFAULT_GAP = 0.45
SAMPLE_RATE = 44100


async def synthesize_clip(text: str, output: Path, voice: str, rate: str) -> None:
    """使用 Edge TTS 合成单段旁白音频（MP3）。"""
    output.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(output))


def wav_duration(path: Path) -> float:
    """读取 WAV 文件时长（秒）。"""
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / float(audio.getframerate())


def _mp3_to_wav(mp3: Path, wav: Path) -> None:
    """将 MP3 转为单声道 44.1kHz WAV。"""
    run_ffmpeg(
        [
            "-hide_banner",
            "-y",
            "-i",
            str(mp3),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            str(wav),
        ]
    )


def write_silence_wav(path: Path, duration: float, *, sample_rate: int = SAMPLE_RATE) -> None:
    """写入指定时长的单声道静音 WAV（与旁白采样率一致）。"""
    if duration <= 0:
        raise ValueError("silence duration 必须为正数")
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(round(duration * sample_rate))
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"\x00\x00" * frames)


def build_concat_list(clip_paths: list[Path], silence_path: Path) -> list[Path]:
    """在旁白片段之间插入静音，使拼接时长与字幕时间轴一致。"""
    if not clip_paths:
        return []
    entries: list[Path] = [clip_paths[0]]
    for clip in clip_paths[1:]:
        entries.append(silence_path)
        entries.append(clip)
    return entries


def concat_audio(paths: RunPaths, clip_paths: list[Path], output: Path) -> None:
    """用 ffmpeg concat 将多段 WAV 合并为 narration.wav。"""
    list_path = paths.work_audio_dir / "edge_concat.txt"
    list_path.write_text(
        "\n".join(f"file '{clip.as_posix()}'" for clip in clip_paths) + "\n",
        encoding="utf-8",
    )
    run_ffmpeg(
        [
            "-hide_banner",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "1",
            str(output),
        ]
    )


async def build_narration(
    paths: RunPaths,
    *,
    voice_id: str,
    voice_rate: str,
    gap: float = DEFAULT_GAP,
) -> list[dict]:
    """为 draft 状态的分段合成配音、生成字幕并更新运行状态。

    旁白与字幕一律以 TTS 实际时长为准；`expected_duration` 仅作规划参考，
    不得用 atempo 加速或截断来凑预估时长。段间插入 `gap` 秒静音。

    返回字幕时间轴列表（start/end 为秒）。
    """
    data = load_segments(paths)
    if data.get("status") != "draft":
        raise ValueError(f"segments.json 状态须为 draft，当前为: {data.get('status')!r}")

    paths.ensure_dirs()
    clips_dir = paths.work_audio_dir / "edge_clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    segments = data["segments"]
    clip_paths: list[Path] = []
    timings: list[dict] = []
    cursor = 0.0

    for index, segment in enumerate(segments, start=1):
        mp3 = clips_dir / f"clip_{index:03d}.mp3"
        wav = clips_dir / f"clip_{index:03d}.wav"

        await synthesize_clip(segment["text"], mp3, voice_id, voice_rate)
        _mp3_to_wav(mp3, wav)
        actual_duration = wav_duration(wav)
        clip_paths.append(wav)

        segment["start"] = srt_time(cursor)
        segment["actual_duration"] = actual_duration
        cursor += actual_duration
        segment["end"] = srt_time(cursor)
        cursor += gap

        timings.append(
            {
                "start": parse_srt_time(segment["start"]),
                "end": parse_srt_time(segment["end"]),
                "text": segment["text"],
            }
        )

    silence_path = paths.work_audio_dir / "silence_gap.wav"
    if gap > 0 and len(clip_paths) > 1:
        write_silence_wav(silence_path, gap)
        concat_entries = build_concat_list(clip_paths, silence_path)
    else:
        concat_entries = list(clip_paths)

    concat_audio(paths, concat_entries, paths.narration_wav)
    write_subtitles(timings, paths.captions_srt, paths.captions_ass)

    data["status"] = "narrated"
    save_segments(paths, data)
    update_run_status(paths, "narrated")

    return timings


def main() -> None:
    parser = argparse.ArgumentParser(description="Edge TTS 配音与字幕生成")
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="运行输出目录（含 segments.json）",
    )
    parser.add_argument(
        "--voice-id",
        default=DEFAULT_VOICE_ID,
        help=f"Edge TTS 语音 ID（默认: {DEFAULT_VOICE_ID}）",
    )
    parser.add_argument(
        "--voice-rate",
        default=DEFAULT_VOICE_RATE,
        help="语速调整（默认: -3%%）",
    )
    parser.add_argument(
        "--gap",
        type=float,
        default=DEFAULT_GAP,
        help=f"段间间隔秒数（默认: {DEFAULT_GAP}）",
    )
    args = parser.parse_args()

    paths = RunPaths(args.output_dir.resolve())
    timings = asyncio.run(
        build_narration(
            paths,
            voice_id=args.voice_id,
            voice_rate=args.voice_rate,
            gap=args.gap,
        )
    )
    print(f"已生成配音: {paths.narration_wav}")
    print(f"已生成字幕: {paths.captions_srt}, {paths.captions_ass}")
    print(f"共 {len(timings)} 段，状态已更新为 narrated")


if __name__ == "__main__":
    main()

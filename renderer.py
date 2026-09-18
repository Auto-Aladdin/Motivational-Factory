
"""
Motivational Factory V6.1 Premium Shorts Renderer

Features:
- Production brief + visual assets compatible
- Real audio duration driven scene timing
- Whisper-compatible word timing captions
- Premium mobile-first caption compositor
- Cinematic background grading
- Vertical 1080x1920 output
- Graceful asset fallback
- Final MP4 in output/final_short.mp4

Dependencies:
moviepy
Pillow
numpy
faster-whisper (optional but recommended)
"""

import json
import subprocess
from pathlib import Path

try:
    # MoviePy 1.x compatibility
    from moviepy.editor import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        concatenate_videoclips,
        ColorClip,
        TextClip,
        vfx
    )
except ModuleNotFoundError:
    # MoviePy 2.x compatibility
    from moviepy import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        concatenate_videoclips,
        ColorClip,
        TextClip,
        vfx
    )

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

FINAL_VIDEO = OUTPUT / "final_short.mp4"

WIDTH = 1080
HEIGHT = 1920


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_audio_duration():
    voice = OUTPUT / "voice.wav"
    if not voice.exists():
        return 60

    return AudioFileClip(str(voice)).duration


def fit_vertical(clip):
    clip = clip.resize(height=HEIGHT)

    if clip.w < WIDTH:
        clip = clip.resize(width=WIDTH)

    return clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=WIDTH,
        height=HEIGHT
    )


def cinematic_grade(clip):
    overlay = ColorClip(
        (WIDTH, HEIGHT),
        color=(0, 0, 0),
        duration=clip.duration
    ).set_opacity(0.42)

    return CompositeVideoClip(
        [clip, overlay]
    )


def download(url, name):
    import requests

    path = OUTPUT / name

    if path.exists():
        return path

    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path.write_bytes(r.content)

    return path


def create_visual(asset, duration):
    if not asset:
        return ColorClip(
            (WIDTH, HEIGHT),
            color=(10, 10, 10),
            duration=duration
        )

    url = asset.get("video_file") or asset.get("image")

    if not url:
        return ColorClip(
            (WIDTH, HEIGHT),
            color=(10, 10, 10),
            duration=duration
        )

    is_video = bool(asset.get("video_file"))

    path = download(
        url,
        f"asset_{asset.get('id','x')}.mp4" if is_video else f"asset_{asset.get('id','x')}.jpg"
    )

    if is_video:
        clip = VideoFileClip(str(path))
        clip = clip.subclip(0, min(duration, clip.duration))
    else:
        clip = ImageClip(str(path)).set_duration(duration)
        clip = clip.resize(
            lambda t: 1.02 + 0.015*t
        )

    return cinematic_grade(
        fit_vertical(clip)
    )


def caption_segments(audio_path):
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "base",
            compute_type="int8"
        )

        segments, _ = model.transcribe(
            str(audio_path),
            word_timestamps=True
        )

        words = []

        for seg in segments:
            for word in seg.words:
                words.append({
                    "text": word.word.strip(),
                    "start": word.start,
                    "end": word.end
                })

        return words

    except Exception:
        return []


def make_caption(text, start, end):
    duration = max(0.4, end-start)

    txt = TextClip(
        text.upper(),
        fontsize=80,
        font="DejaVu-Sans-Bold",
        color="white",
        stroke_color="black",
        stroke_width=3,
        method="caption",
        size=(900, None),
        align="center"
    )

    txt = txt.set_position(
        ("center", 1350)
    )

    return txt.set_start(start).set_duration(duration)


def build_captions(narration):
    audio = OUTPUT / "voice.wav"

    if not audio.exists():
        return []

    timings = caption_segments(audio)

    if not timings:
        return [
            make_caption(
                narration,
                0,
                get_audio_duration()
            )
        ]

    clips = []

    chunk = []

    for word in timings:
        chunk.append(word)

        if len(chunk) >= 4 or word["text"].endswith((".", "!", "?")):
            text = " ".join(
                x["text"] for x in chunk
            )

            clips.append(
                make_caption(
                    text,
                    chunk[0]["start"],
                    chunk[-1]["end"]
                )
            )

            chunk = []

    return clips


def render():

    print("V6.1 Premium Renderer Starting")

    brief = load_json(
        OUTPUT / "production_brief.json"
    )

    assets = load_json(
        OUTPUT / "visual_assets.json"
    )

    total = get_audio_duration()

    scene_count = len(
        brief.get("scenes", [])
    )

    duration = total / max(scene_count, 1)

    clips = []

    for scene in brief.get("scenes", []):

        group = next(
            (
                x for x in assets.get("videos", [])
                if x.get("scene") == scene.get("scene")
            ),
            {}
        )

        candidates = group.get("videos", [])

        asset = candidates[0] if candidates else None

        clips.append(
            create_visual(
                asset,
                duration
            )
        )

    video = concatenate_videoclips(
        clips,
        method="compose"
    )

    if (OUTPUT / "voice.wav").exists():
        voice = AudioFileClip(
            str(OUTPUT / "voice.wav")
        )

        audio_tracks = [voice]

        if (OUTPUT / "music.mp3").exists():
            music = AudioFileClip(
                str(OUTPUT / "music.mp3")
            ).volumex(0.15)

            audio_tracks.append(music)

        video = video.set_audio(
            CompositeAudioClip(audio_tracks)
        )

    caption_layers = build_captions(
        brief.get("narration", "")
    )

    final = CompositeVideoClip(
        [video] + caption_layers,
        size=(WIDTH, HEIGHT)
    )

    final.write_videofile(
        str(FINAL_VIDEO),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium"
    )

    print("DONE:", FINAL_VIDEO)


if __name__ == "__main__":
    render()

"""
Motivational Factory V6.2 Premium Shorts Renderer

Preserves the existing production pipeline while adding:
- MoviePy 2.x compatibility
- Accurate reuse of the existing caption_plan.json
- Centered cinematic/viral-style captions
- Word-by-word active highlighting
- Power-word emphasis
- Multiple typography styles selected from the video's theme
- Optional music support
- Automatic cleanup of only downloaded visual asset files
- Final MP4 output remains output/final_short.mp4
"""

import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        concatenate_videoclips,
        ColorClip,
        TextClip,
    )
except ImportError:
    from moviepy.editor import (
        VideoFileClip,
        ImageClip,
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        concatenate_videoclips,
        ColorClip,
        TextClip,
    )


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

FINAL_VIDEO = OUTPUT / "final_short.mp4"

WIDTH = 1080
HEIGHT = 1920

FONT_CACHE = Path(".font_cache")
FONT_CACHE.mkdir(exist_ok=True)

# Open-source display fonts. They are downloaded only when the runner
# does not already have them installed, and are kept outside output/.
FONT_DOWNLOADS = {
    "Montserrat ExtraBold": (
        "https://github.com/google/fonts/raw/main/ofl/montserrat/static/"
        "Montserrat-ExtraBold.ttf"
    ),
    "Anton": (
        "https://github.com/google/fonts/raw/main/ofl/anton/"
        "Anton-Regular.ttf"
    ),
    "Poppins ExtraBold": (
        "https://github.com/google/fonts/raw/main/ofl/poppins/static/"
        "Poppins-ExtraBold.ttf"
    ),
    "Bebas Neue": (
        "https://github.com/google/fonts/raw/main/ofl/bebasneue/"
        "BebasNeue-Regular.ttf"
    ),
}

CAPTION_STYLES = {
    "montserrat": {
        "name": "Montserrat ExtraBold",
        "font_size": 104,
        "active_size_bonus": 10,
        "highlight": "#FFD447",
    },
    "anton": {
        "name": "Anton",
        "font_size": 112,
        "active_size_bonus": 12,
        "highlight": "#FFD447",
    },
    "poppins": {
        "name": "Poppins ExtraBold",
        "font_size": 104,
        "active_size_bonus": 10,
        "highlight": "#37E7FF",
    },
    "bebas": {
        "name": "Bebas Neue",
        "font_size": 116,
        "active_size_bonus": 12,
        "highlight": "#75F078",
    },
    "helvetica": {
        "name": "Helvetica",
        "font_size": 100,
        "active_size_bonus": 10,
        "highlight": "#37E7FF",
    },
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_audio_duration():
    voice = OUTPUT / "voice.wav"

    if not voice.exists():
        return 60

    clip = AudioFileClip(str(voice))

    try:
        return float(clip.duration)
    finally:
        close_quietly(clip)


def close_quietly(clip):
    try:
        if clip is not None:
            clip.close()
    except Exception:
        pass


def fit_vertical(clip):
    clip = clip.resized(height=HEIGHT)

    if clip.w < WIDTH:
        clip = clip.resized(width=WIDTH)

    if hasattr(clip, "cropped"):
        return clip.cropped(
            x_center=clip.w / 2,
            y_center=clip.h / 2,
            width=WIDTH,
            height=HEIGHT,
        )

    return clip.crop(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=WIDTH,
        height=HEIGHT,
    )


def cinematic_grade(clip):
    overlay = ColorClip(
        (WIDTH, HEIGHT),
        color=(0, 0, 0),
        duration=clip.duration,
    ).with_opacity(0.42)

    return CompositeVideoClip([clip, overlay])


def download(url, name):
    import requests

    path = OUTPUT / name

    if path.exists():
        return path

    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.write_bytes(response.content)

    return path


def create_visual(asset, duration):
    if not asset:
        return ColorClip(
            (WIDTH, HEIGHT),
            color=(10, 10, 10),
            duration=duration,
        )

    url = asset.get("video_file") or asset.get("image")

    if not url:
        return ColorClip(
            (WIDTH, HEIGHT),
            color=(10, 10, 10),
            duration=duration,
        )

    is_video = bool(asset.get("video_file"))

    path = download(
        url,
        (
            f"asset_{asset.get('id', 'x')}.mp4"
            if is_video
            else f"asset_{asset.get('id', 'x')}.jpg"
        ),
    )

    if is_video:
        clip = VideoFileClip(str(path))
        clip = clip.subclipped(
            0,
            min(duration, clip.duration),
        )
    else:
        clip = ImageClip(str(path)).with_duration(duration)

    return cinematic_grade(
        fit_vertical(clip)
    )


def _fc_match(pattern):
    """Return a system font path when fontconfig has a matching font."""
    try:
        result = subprocess.run(
            [
                "fc-match",
                "-f",
                "%{file}",
                pattern,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )

        path = result.stdout.strip()

        if path and Path(path).exists():
            return Path(path)

    except Exception:
        pass

    return None


def _download_font(name, url):
    destination = FONT_CACHE / Path(url).name

    if destination.exists():
        return destination

    try:
        import requests

        response = requests.get(
            url,
            timeout=30,
        )
        response.raise_for_status()

        destination.write_bytes(response.content)

        return destination

    except Exception as exc:
        print(
            f"Font download skipped for {name}: {exc}"
        )

    return None


def resolve_font(name):
    """
    Prefer the requested display font.

    Falls back to common system fonts if the exact family is unavailable.
    """
    system_patterns = {
        "Montserrat ExtraBold": [
            "Montserrat:style=ExtraBold",
            "Montserrat:style=Black",
        ],
        "Anton": [
            "Anton",
        ],
        "Poppins ExtraBold": [
            "Poppins:style=ExtraBold",
            "Poppins:style=Bold",
        ],
        "Bebas Neue": [
            "Bebas Neue",
            "BebasNeue",
        ],
        "Helvetica": [
            "Helvetica:style=Bold",
            "Arial:style=Bold",
            "Nimbus Sans:style=Bold",
        ],
    }

    for pattern in system_patterns.get(name, [name]):
        path = _fc_match(pattern)

        if path is not None:
            family_text = path.name.lower()

            # If fontconfig returned a fallback rather than the requested
            # family, keep searching before accepting a generic font.
            requested_tokens = [
                token
                for token in name.lower().replace("-", " ").split()
                if token not in {"extra", "bold"}
            ]

            if any(token in family_text for token in requested_tokens):
                return path

    if name in FONT_DOWNLOADS:
        downloaded = _download_font(
            name,
            FONT_DOWNLOADS[name],
        )

        if downloaded is not None:
            return downloaded

    # Reliable final fallbacks available on standard Ubuntu runners.
    for pattern in (
        "DejaVu Sans:style=Bold",
        "Noto Sans:style=ExtraBold",
        "Nimbus Sans:style=Bold",
    ):
        path = _fc_match(pattern)

        if path is not None:
            return path

    return None


def select_caption_style(brief):
    """
    Select one coherent typography style per video rather than changing
    fonts randomly from line to line.
    """
    creative = brief.get(
        "creative_direction",
        {},
    )

    voice = brief.get(
        "voice_direction",
        {},
    )

    searchable = " ".join(
        [
            str(brief.get("title", "")),
            str(brief.get("theme", "")),
            str(creative.get("philosophical_theme", "")),
            str(creative.get("emotional_arc", "")),
            str(creative.get("visual_style", "")),
            str(voice.get("personality", "")),
            str(voice.get("emotion", "")),
        ]
    ).lower()

    power_words = (
        "warrior",
        "sacrifice",
        "achievement",
        "resilience",
        "fear",
        "failure",
        "battle",
        "strength",
        "power",
        "overcome",
        "intense",
    )

    hope_words = (
        "hope",
        "healing",
        "reflection",
        "transformation",
        "growth",
        "peace",
        "change",
    )

    discipline_words = (
        "stoic",
        "discipline",
        "wisdom",
        "philosophy",
        "self-control",
        "focus",
        "mindset",
    )

    modern_words = (
        "future",
        "modern",
        "technology",
        "innovation",
    )

    if any(word in searchable for word in power_words):
        selected = "anton"
    elif any(word in searchable for word in hope_words):
        selected = "poppins"
    elif any(word in searchable for word in modern_words):
        selected = "helvetica"
    elif any(word in searchable for word in discipline_words):
        selected = "montserrat"
    else:
        selected = "montserrat"

    style = dict(CAPTION_STYLES[selected])
    style["font_path"] = resolve_font(style["name"])

    return style


def _load_font(font_path, size):
    """Load the selected font with a safe DejaVu fallback."""
    try:
        if font_path:
            return ImageFont.truetype(
                str(font_path),
                size,
            )
    except Exception:
        pass

    fallback = _fc_match("DejaVu Sans:style=Bold")

    if fallback is not None:
        try:
            return ImageFont.truetype(
                str(fallback),
                size,
            )
        except Exception:
            pass

    return ImageFont.load_default()


def _word_size(draw, word, font, stroke_width):
    bbox = draw.textbbox(
        (0, 0),
        word,
        font=font,
        stroke_width=stroke_width,
    )

    return (
        max(1, bbox[2] - bbox[0]),
        max(1, bbox[3] - bbox[1]),
    )


def _layout_caption_words(words, style):
    """Create centered one- or two-line word positions for a caption."""
    font_size = style["font_size"]
    font = _load_font(
        style["font_path"],
        font_size,
    )

    draw = ImageDraw.Draw(
        Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    )

    max_width = 950
    gap = 18

    measured = []

    for item in words:
        word = str(item["word"]).upper()
        width, height = _word_size(
            draw,
            word,
            font,
            5,
        )

        measured.append(
            {
                **item,
                "word": word,
                "width": width,
                "height": height,
            }
        )

    lines = []
    current = []
    current_width = 0

    for item in measured:
        required = (
            item["width"]
            if not current
            else gap + item["width"]
        )

        if current and current_width + required > max_width:
            lines.append(current)
            current = [item]
            current_width = item["width"]
        else:
            current.append(item)
            current_width += required

    if current:
        lines.append(current)

    line_gap = 18
    line_heights = [
        max(item["height"] for item in line)
        for line in lines
    ]

    total_height = (
        sum(line_heights)
        + line_gap * max(0, len(lines) - 1)
    )

    start_y = HEIGHT / 2 - total_height / 2
    positions = []

    current_y = start_y

    for line_index, line in enumerate(lines):
        line_height = line_heights[line_index]
        line_width = (
            sum(item["width"] for item in line)
            + gap * max(0, len(line) - 1)
        )

        x = WIDTH / 2 - line_width / 2

        for item in line:
            positions.append(
                {
                    **item,
                    "x": x,
                    "y": current_y + (line_height - item["height"]) / 2,
                    "line_height": line_height,
                }
            )

            x += item["width"] + gap

        current_y += line_height + line_gap

    return positions


def _caption_frame(words, active_index, style):
    """Render one complete caption frame with one active word emphasized."""
    image = Image.new(
        "RGBA",
        (WIDTH, HEIGHT),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(image)

    font = _load_font(
        style["font_path"],
        style["font_size"],
    )

    active_font = _load_font(
        style["font_path"],
        style["font_size"] + style["active_size_bonus"],
    )

    positions = _layout_caption_words(
        words,
        style,
    )

    for index, item in enumerate(positions):
        word = item["word"]
        x = item["x"]
        y = item["y"]

        is_active = index == active_index

        draw_font = active_font if is_active else font
        color = "#FFFFFF"
        stroke_width = 6

        if is_active:
            color = item.get("color") or style["highlight"]

            if str(color).upper() == "#FFFFFF":
                color = style["highlight"]

            style_name = str(
                item.get("style", "normal")
            ).lower()

            if style_name in {
                "pain",
                "highlight",
                "impact",
            } and item.get("color"):
                color = item["color"]

            # Center the slightly larger active word over the same word slot.
            normal_w, normal_h = _word_size(
                draw,
                word,
                font,
                6,
            )

            active_w, active_h = _word_size(
                draw,
                word,
                active_font,
                6,
            )

            x += (normal_w - active_w) / 2
            y += (normal_h - active_h) / 2

        draw.text(
            (x, y),
            word,
            font=draw_font,
            fill=color,
            stroke_width=stroke_width,
            stroke_fill="#000000",
        )

    return np.asarray(image)


def _caption_words(segment):
    words = segment.get("words", [])

    if isinstance(words, list) and words:
        return [
            {
                "word": str(item.get("word", "")).strip(),
                "start": float(
                    item.get(
                        "start",
                        segment.get("start", 0),
                    )
                ),
                "end": float(
                    item.get(
                        "end",
                        segment.get("end", 0),
                    )
                ),
                "style": str(
                    item.get(
                        "style",
                        "normal",
                    )
                ),
                "color": str(
                    item.get(
                        "color",
                        "#FFFFFF",
                    )
                ),
            }
            for item in words
            if str(item.get("word", "")).strip()
        ]

    raw_text = str(
        segment.get("text", "")
    ).strip()

    if not raw_text:
        return []

    start = float(
        segment.get(
            "start",
            0,
        )
    )

    end = float(
        segment.get(
            "end",
            start + 0.4,
        )
    )

    tokens = raw_text.split()

    word_duration = max(
        0.05,
        (end - start) / max(len(tokens), 1),
    )

    generated = []

    for index, token in enumerate(tokens):
        token_start = start + index * word_duration
        token_end = (
            end
            if index == len(tokens) - 1
            else token_start + word_duration
        )

        generated.append(
            {
                "word": token,
                "start": token_start,
                "end": token_end,
                "style": "normal",
                "color": "#FFFFFF",
            }
        )

    return generated


def _segment_caption_clips(segment, style):
    words = _caption_words(segment)

    if not words:
        return []

    clips = []

    for index, word in enumerate(words):
        frame = _caption_frame(
            words,
            index,
            style,
        )

        duration = max(
            0.05,
            float(word["end"]) - float(word["start"]),
        )

        clip = ImageClip(
            frame,
        ).with_start(
            float(word["start"])
        ).with_duration(
            duration
        ).with_position(
            (0, 0)
        )

        clips.append(clip)

    return clips


def _load_caption_plan():
    path = OUTPUT / "caption_plan.json"

    if not path.exists():
        return []

    try:
        data = load_json(path)

        if isinstance(data, list):
            valid = [
                segment
                for segment in data
                if isinstance(segment, dict)
                and (
                    segment.get("words")
                    or segment.get("text")
                )
            ]

            if valid:
                return valid

    except Exception as exc:
        print(
            f"Caption plan could not be loaded: {exc}"
        )

    return []


def caption_segments_fallback(audio_path):
    """
    Fallback only for projects where caption_plan.json is unavailable.
    Normally the already-generated caption plan is reused, avoiding a
    second Whisper pass.
    """
    try:
        from faster_whisper import WhisperModel

        model = WhisperModel(
            "base",
            compute_type="int8",
        )

        segments, _ = model.transcribe(
            str(audio_path),
            word_timestamps=True,
        )

        words = []

        for segment in segments:
            for word in segment.words:
                words.append(
                    {
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end,
                        "style": "normal",
                        "color": "#FFFFFF",
                    }
                )

        if not words:
            return []

        groups = []
        chunk = []

        for word in words:
            chunk.append(word)

            if (
                len(chunk) >= 4
                or word["word"].endswith((".", "!", "?"))
            ):
                groups.append(
                    {
                        "start": chunk[0]["start"],
                        "end": chunk[-1]["end"],
                        "text": " ".join(
                            item["word"]
                            for item in chunk
                        ),
                        "words": chunk,
                    }
                )
                chunk = []

        if chunk:
            groups.append(
                {
                    "start": chunk[0]["start"],
                    "end": chunk[-1]["end"],
                    "text": " ".join(
                        item["word"]
                        for item in chunk
                    ),
                    "words": chunk,
                }
            )

        return groups

    except Exception as exc:
        print(
            f"Caption timing fallback failed: {exc}"
        )
        return []


def build_captions(brief):
    plan = _load_caption_plan()
    using_existing_plan = bool(plan)

    if not plan:
        audio = OUTPUT / "voice.wav"

        if audio.exists():
            plan = caption_segments_fallback(audio)

    if not plan:
        narration = str(
            brief.get("narration", "")
        ).strip()

        if not narration:
            return []

        fallback_duration = get_audio_duration()

        plan = [
            {
                "start": 0,
                "end": fallback_duration,
                "text": narration,
                "words": [
                    {
                        "word": word,
                        "start": 0,
                        "end": fallback_duration,
                        "style": "normal",
                        "color": "#FFFFFF",
                    }
                    for word in narration.split()
                ],
            }
        ]

    style = select_caption_style(brief)

    print(
        "Caption style:",
        style["name"],
        "Highlight:",
        style["highlight"],
    )

    if using_existing_plan:
        print(
            "Using existing caption_plan.json "
            "(skipping duplicate Whisper transcription)."
        )
    else:
        print(
            "Caption plan unavailable; using Whisper fallback."
        )

    caption_layers = []

    for segment in plan:
        caption_layers.extend(
            _segment_caption_clips(
                segment,
                style,
            )
        )

    return caption_layers


def cleanup_visual_assets():
    """
    Delete only large downloaded visual assets produced by this renderer.

    Production JSON files, voice files, caption_plan.json, and
    final_short.mp4 are intentionally preserved.
    """
    removed = 0
    removed_bytes = 0

    extensions = {
        ".mp4",
        ".mov",
        ".m4v",
        ".webm",
        ".avi",
        ".mkv",
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }

    for path in OUTPUT.glob("asset_*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in extensions:
            continue

        try:
            size = path.stat().st_size
            path.unlink()
            removed += 1
            removed_bytes += size

        except Exception as exc:
            print(
                f"Could not delete {path.name}: {exc}"
            )

    if removed:
        print(
            f"Cleaned {removed} temporary visual assets "
            f"({removed_bytes / 1024 / 1024:.1f} MB)."
        )
    else:
        print(
            "No temporary visual assets required cleanup."
        )


def render():
    print("V6.2 Premium Renderer Starting")

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

    duration = total / max(
        scene_count,
        1,
    )

    clips = []

    for scene in brief.get("scenes", []):
        group = next(
            (
                item
                for item in assets.get("videos", [])
                if item.get("scene") == scene.get("scene")
            ),
            {},
        )

        candidates = group.get(
            "videos",
            [],
        )

        asset = (
            candidates[0]
            if candidates
            else None
        )

        clips.append(
            create_visual(
                asset,
                duration,
            )
        )

    if not clips:
        raise RuntimeError(
            "No visual assets were available for rendering."
        )

    video = concatenate_videoclips(
        clips,
        method="compose",
    )

    audio_objects = []

    try:
        voice_path = OUTPUT / "voice.wav"

        if voice_path.exists():
            voice = AudioFileClip(
                str(voice_path)
            )

            audio_objects.append(voice)

            music_path = OUTPUT / "music.mp3"

            if music_path.exists():
                music = AudioFileClip(
                    str(music_path)
                ).with_volume_scaled(0.15)

                audio_objects.append(music)

            video = video.with_audio(
                CompositeAudioClip(
                    audio_objects
                )
            )

        caption_layers = build_captions(
            brief
        )

        final = CompositeVideoClip(
            [video] + caption_layers,
            size=(WIDTH, HEIGHT),
        )

        final.write_videofile(
            str(FINAL_VIDEO),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
        )

        if not FINAL_VIDEO.exists():
            raise RuntimeError(
                "Renderer finished without creating final_short.mp4."
            )

        print(
            "DONE:",
            FINAL_VIDEO,
        )

    finally:
        # Close MoviePy resources before deleting source asset files.
        for layer in clips:
            close_quietly(layer)

        for audio in audio_objects:
            close_quietly(audio)

        close_quietly(video)

        if "final" in locals():
            close_quietly(final)

    # Keep all useful production artifacts, but remove only the large
    # downloaded visual source files after a successful final render.
    cleanup_visual_assets()


if __name__ == "__main__":
    render()

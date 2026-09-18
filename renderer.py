"""
Motivational Factory Premium Shorts Renderer

Targeted output-layer improvements only:
- MoviePy 2.x-compatible TextClip usage
- Uses the existing caption_plan.json instead of re-running Whisper
- True visual-center caption placement
- Word-by-word active highlighting
- Power-word pop emphasis
- Story-aware typography with multiple font families when installed
- Keeps caption/JSON/audio/final-video files
- Removes only large temporary downloaded media after a successful render

Core story, quality-gate, Pexels selection, voice, JSON, and pipeline logic
remain unchanged.
"""

import json
import os
import re
from difflib import SequenceMatcher
from pathlib import Path

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
        concatenate_videoclips,
        ColorClip,
        TextClip,
    )

OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

FINAL_VIDEO = OUTPUT / "final_short.mp4"

WIDTH = 1080
HEIGHT = 1920

# =====================================================
# CAPTION SETTINGS
# =====================================================

CAPTION_MAX_WIDTH = 920
CAPTION_MIN_FONT_SIZE = 60
CAPTION_FONT_SIZE = 84
CAPTION_STROKE = 6
CAPTION_SPACING = 14
CAPTION_CENTER_X = WIDTH / 2
CAPTION_CENTER_Y = HEIGHT / 2
CAPTION_POP_DURATION = 0.11

# Existing caption-plan colors are preserved.
DEFAULT_NORMAL = "#FFFFFF"
DEFAULT_HIGHLIGHT = "#FFD447"
DEFAULT_PAIN = "#FF5555"
DEFAULT_HOPE = "#45E6FF"

# Large temporary source assets created by this renderer.
TEMP_ASSET_PATTERNS = (
    "asset_*.mp4",
    "asset_*.mov",
    "asset_*.webm",
    "asset_*.jpg",
    "asset_*.jpeg",
    "asset_*.png",
    "asset_*.webp",
)


# =====================================================
# BASIC HELPERS
# =====================================================


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_close(clip):
    if clip is None:
        return
    try:
        clip.close()
    except Exception:
        pass


def get_audio_duration():
    voice = OUTPUT / "voice.wav"
    if not voice.exists():
        return 60

    clip = AudioFileClip(str(voice))
    try:
        return float(clip.duration)
    finally:
        safe_close(clip)


# =====================================================
# VIDEO FIT / GRADE
# =====================================================


def fit_vertical(clip):
    clip = clip.resized(height=HEIGHT)

    if clip.w < WIDTH:
        clip = clip.resized(width=WIDTH)

    # MoviePy 2.x renamed crop -> cropped
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


# =====================================================
# ASSET DOWNLOAD
# =====================================================


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
        f"asset_{asset.get('id','x')}.mp4"
        if is_video
        else f"asset_{asset.get('id','x')}.jpg",
    )

    if is_video:
        clip = VideoFileClip(str(path))
        clip = clip.subclipped(0, min(duration, clip.duration))
    else:
        clip = ImageClip(str(path)).with_duration(duration)

    return cinematic_grade(fit_vertical(clip))


# =====================================================
# CAPTION FONT RESOLUTION
# =====================================================


def _find_font_file(patterns):
    """Find an exact/near-exact font file in common system/repository paths."""
    roots = [
        Path.cwd() / "fonts",
        OUTPUT.parent / "fonts",
        Path("/usr/share/fonts"),
        Path("/usr/local/share/fonts"),
        Path.home() / ".fonts",
    ]

    wanted = [p.lower() for p in patterns]

    for root in roots:
        if not root.exists():
            continue

        try:
            candidates = root.rglob("*")
        except Exception:
            continue

        for candidate in candidates:
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in {".ttf", ".otf"}:
                continue

            name = candidate.name.lower()
            if any(token in name for token in wanted):
                return str(candidate)

    return None


def resolve_caption_font(theme):
    """
    Prefer the requested style fonts when they are installed.
    GitHub/Linux runners may not ship proprietary fonts, so safe open-font
    fallbacks are provided without changing the visual hierarchy.
    """

    exact = {
        "montserrat": [
            "montserrat-extrabold",
            "montserrat-black",
            "montserrat-bold",
        ],
        "anton": [
            "anton-regular",
            "anton",
        ],
        "impact": [
            "impact",
        ],
        "sfpro": [
            "sf-pro-display-bold",
            "sfprodisplay-bold",
            "sfprodisplay",
        ],
        "helvetica": [
            "helvetica-bold",
            "helvetica-neue-bold",
            "helvetica",
        ],
    }

    fallbacks = {
        "montserrat": [
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ],
        "anton": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
        ],
        "impact": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
        ],
        "sfpro": [
            "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "helvetica": [
            "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
    }

    exact_path = _find_font_file(exact.get(theme, []))
    if exact_path:
        return exact_path

    for fallback in fallbacks.get(theme, []):
        if Path(fallback).exists():
            return fallback

    return None


def choose_caption_theme(narration, caption_plan=None):
    """Pick a deterministic typography personality from the story topic."""
    text = str(narration or "").lower()

    themes = {
        "anton": {
            "never", "quit", "fight", "hard", "grind", "discipline",
            "sacrifice", "challenge", "prove", "strong", "strength",
            "pain", "failure", "comeback", "rise", "battle", "win",
        },
        "montserrat": {
            "success", "business", "work", "career", "money", "wealth",
            "focus", "productivity", "goal", "goals", "growth",
            "confidence", "achievement", "discipline",
        },
        "impact": {
            "warning", "danger", "fear", "broken", "lost", "alone",
            "failure", "regret", "destroy", "destroyed", "escape",
            "stop", "wake", "truth",
        },
        "sfpro": {
            "life", "future", "purpose", "meaning", "mind", "choice",
            "time", "today", "tomorrow", "believe", "thought",
            "philosophy", "journey", "identity",
        },
    }

    scores = {
        theme: sum(1 for keyword in words if re.search(rf"\b{re.escape(keyword)}\b", text))
        for theme, words in themes.items()
    }

    # If the plan contains many hope words, favor the cleaner premium style.
    if caption_plan:
        styled = [
            word
            for item in caption_plan
            for word in item.get("words", [])
        ]
        hope_count = sum(
            1 for word in styled
            if str(word.get("style", "")).lower() == "hope"
        )
        if hope_count >= 2:
            scores["sfpro"] += 2

    best = max(scores, key=scores.get) if scores else "montserrat"
    return best if scores.get(best, 0) > 0 else "montserrat"


# =====================================================
# CAPTION DATA
# =====================================================


def _normalize_caption_plan(plan):
    """Normalize the existing caption plan without modifying its JSON file."""
    normalized = []

    if not isinstance(plan, list):
        return normalized

    for item in plan:
        if not isinstance(item, dict):
            continue

        words = []
        for word in item.get("words", []):
            if not isinstance(word, dict):
                continue

            text = str(word.get("word", "")).strip()
            if not text:
                continue

            try:
                start = float(word.get("start", item.get("start", 0)))
                end = float(word.get("end", item.get("end", start + 0.25)))
            except (TypeError, ValueError):
                continue

            if end <= start:
                end = start + 0.25

            words.append(
                {
                    "word": text.upper(),
                    "start": start,
                    "end": end,
                    "style": str(word.get("style", "normal")),
                    "color": str(word.get("color", DEFAULT_NORMAL)),
                    "animation": str(word.get("animation", "fade")),
                }
            )

        if not words:
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            try:
                start = float(item.get("start", 0))
                end = float(item.get("end", start + 0.8))
            except (TypeError, ValueError):
                continue
            words = [
                {
                    "word": w,
                    "start": start,
                    "end": end,
                    "style": "normal",
                    "color": DEFAULT_NORMAL,
                    "animation": "fade",
                }
                for w in text.upper().split()
            ]

        try:
            group_start = float(item.get("start", words[0]["start"]))
            group_end = float(item.get("end", words[-1]["end"]))
        except (TypeError, ValueError):
            group_start = words[0]["start"]
            group_end = words[-1]["end"]

        if group_end <= group_start:
            group_end = max(group_start + 0.4, words[-1]["end"])

        normalized.append(
            {
                "start": group_start,
                "end": group_end,
                "words": words,
            }
        )

    return normalized


def load_caption_plan():
    path = OUTPUT / "caption_plan.json"
    if not path.exists():
        return []

    try:
        return _normalize_caption_plan(load_json(path))
    except Exception as exc:
        print("Caption plan could not be loaded:", exc)
        return []


def _normalize_token(value):
    """Normalize a caption/audio word for robust sequence matching."""
    value = str(value or "").lower().strip()
    value = re.sub(r"[^a-z0-9']+", "", value)
    return value


def _narration_tokens(narration):
    return re.findall(r"\b[\w']+\b", str(narration or ""))


def _flatten_plan_words(plan):
    flattened = []
    for item in plan or []:
        for word in item.get("words", []):
            flattened.append(dict(word))
    return flattened


def _plan_matches_narration(plan, narration):
    planned = [
        _normalize_token(word.get("word", ""))
        for word in _flatten_plan_words(plan)
        if _normalize_token(word.get("word", ""))
    ]
    target = [
        _normalize_token(word)
        for word in _narration_tokens(narration)
        if _normalize_token(word)
    ]

    if not planned or not target:
        return False

    matcher = SequenceMatcher(None, target, planned, autojunk=False)
    ratio = matcher.ratio()
    return planned == target or ratio >= 0.96


def _plan_has_real_audio_timing(plan, audio_duration):
    """Reject legacy fixed 0.35s fallback timing from older caption plans."""
    words = _flatten_plan_words(plan)
    if not words or audio_duration <= 0:
        return False

    starts = []
    ends = []
    fixed_count = 0

    for word in words:
        try:
            start = float(word.get("start", 0))
            end = float(word.get("end", 0))
        except (TypeError, ValueError):
            return False

        if end <= start:
            return False

        starts.append(start)
        ends.append(end)
        if abs((end - start) - 0.35) < 0.015:
            fixed_count += 1

    if starts != sorted(starts):
        return False

    # A plan where essentially every word is exactly 0.35s is the old
    # narration-only fallback and is not safely synchronized to voice.wav.
    if len(words) >= 3 and fixed_count / len(words) >= 0.85:
        return False

    # Do not accept timestamps that run materially beyond the real audio.
    if max(ends) > audio_duration + 0.35:
        return False

    return True


def _weighted_time_split(start, end, words):
    """Split an audio time range over words using character length weights."""
    count = len(words)
    if count == 0:
        return []

    start = float(start)
    end = max(start, float(end))
    weights = [max(1, len(_normalize_token(w))) for w in words]
    total_weight = float(sum(weights)) or float(count)

    cursor = start
    result = []
    for index, weight in enumerate(weights):
        if index == count - 1:
            next_cursor = end
        else:
            next_cursor = cursor + (end - start) * (weight / total_weight)
        result.append((cursor, next_cursor))
        cursor = next_cursor
    return result


def _align_whisper_words(narration, whisper_words, audio_duration):
    """
    Force the spoken-word timestamps onto the exact narration token sequence.

    Whisper may normalize punctuation, merge/split words, or occasionally miss
    a word. The alignment layer therefore uses sequence matching first and
    interpolates only unmatched runs. This prevents captions from displaying
    narration in the wrong temporal order when the transcript differs slightly.
    """
    target_words = _narration_tokens(narration)
    transcript = [
        item for item in (whisper_words or [])
        if _normalize_token(item.get("word", ""))
    ]

    if not target_words or not transcript:
        return []

    target_norm = [_normalize_token(w) for w in target_words]
    transcript_norm = [_normalize_token(w.get("word", "")) for w in transcript]

    matcher = SequenceMatcher(
        None,
        target_norm,
        transcript_norm,
        autojunk=False,
    )

    aligned = [None] * len(target_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                try:
                    start = float(transcript[j]["start"])
                    end = float(transcript[j]["end"])
                except (TypeError, ValueError, KeyError):
                    continue
                aligned[i] = (start, max(start + 0.01, end))

        elif tag == "replace" and j2 > j1:
            try:
                start = float(transcript[j1]["start"])
                end = float(transcript[j2 - 1]["end"])
            except (TypeError, ValueError, KeyError):
                continue

            split = _weighted_time_split(
                start,
                end,
                target_words[i1:i2],
            )
            for offset, timing in enumerate(split):
                aligned[i1 + offset] = timing

    # Fill any unmatched narration runs from the nearest spoken anchors.
    index = 0
    while index < len(aligned):
        if aligned[index] is not None:
            index += 1
            continue

        run_start = index
        while index < len(aligned) and aligned[index] is None:
            index += 1
        run_end = index

        left_end = 0.0
        if run_start > 0 and aligned[run_start - 1] is not None:
            left_end = aligned[run_start - 1][1]

        right_start = float(audio_duration)
        if run_end < len(aligned) and aligned[run_end] is not None:
            right_start = aligned[run_end][0]

        if right_start < left_end:
            right_start = left_end

        split = _weighted_time_split(
            left_end,
            right_start,
            target_words[run_start:run_end],
        )
        for offset, timing in enumerate(split):
            aligned[run_start + offset] = timing

    # Final monotonicity pass prevents zero/negative or backwards intervals.
    result = []
    previous_end = 0.0
    for word, timing in zip(target_words, aligned):
        if timing is None:
            start = previous_end
            end = min(audio_duration, start + 0.05)
        else:
            start, end = timing
            start = max(previous_end, min(float(audio_duration), start))
            end = max(start + 0.01, min(float(audio_duration), end))

        result.append(
            {
                "word": word,
                "start": round(start, 3),
                "end": round(end, 3),
            }
        )
        previous_end = end

    # Never allow the final caption word to extend past the audio.
    if result:
        result[-1]["end"] = round(min(audio_duration, result[-1]["end"]), 3)
        if result[-1]["end"] <= result[-1]["start"]:
            result[-1]["end"] = round(
                min(audio_duration, result[-1]["start"] + 0.01),
                3,
            )

    return result


def caption_segments(audio_path, narration=None):
    """Return actual word timings from voice.wav, mapped to the narration."""
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
        for seg in segments:
            if not seg.words:
                continue
            for word in seg.words:
                words.append(
                    {
                        "word": word.word.strip(),
                        "start": word.start,
                        "end": word.end,
                    }
                )

        if not words:
            return []

        duration = get_audio_duration()
        if narration:
            return _align_whisper_words(narration, words, duration)
        return words

    except Exception as exc:
        print("Whisper alignment unavailable:", exc)
        return []


def _style_lookup_from_plan(plan):
    """Preserve the existing caption-engine styling for fallback alignment."""
    lookup = {}
    for item in _flatten_plan_words(plan):
        key = _normalize_token(item.get("word", ""))
        if not key or key in lookup:
            continue
        lookup[key] = {
            "style": str(item.get("style", "normal")),
            "color": str(item.get("color", DEFAULT_NORMAL)),
            "animation": str(item.get("animation", "fade")),
        }
    return lookup


def _groups_from_aligned_words(words, plan=None, max_words=5):
    """Build readable caption groups while retaining exact word timings."""
    style_lookup = _style_lookup_from_plan(plan or [])
    groups = []
    current = []

    for raw in words:
        token = str(raw.get("word", "")).strip()
        if not token:
            continue

        style = style_lookup.get(
            _normalize_token(token),
            {
                "style": "normal",
                "color": DEFAULT_NORMAL,
                "animation": "fade",
            },
        )

        current.append(
            {
                "word": token.upper(),
                "start": float(raw["start"]),
                "end": float(raw["end"]),
                **style,
            }
        )

        text = " ".join(x["word"] for x in current)
        if len(current) >= max_words or text.endswith((".", "!", "?")):
            groups.append(
                {
                    "start": current[0]["start"],
                    "end": current[-1]["end"],
                    "words": current,
                }
            )
            current = []

    if current:
        groups.append(
            {
                "start": current[0]["start"],
                "end": current[-1]["end"],
                "words": current,
            }
        )

    return groups


def _rebuild_plan_timing(plan, narration, audio_path):
    """
    Validate the saved caption plan against the actual voice and only replace
    timestamps when the plan came from the old fixed-duration fallback.
    """
    duration = get_audio_duration()

    if (
        plan
        and _plan_matches_narration(plan, narration)
        and _plan_has_real_audio_timing(plan, duration)
    ):
        return plan

    aligned = caption_segments(audio_path, narration)
    if not aligned:
        return []

    return _groups_from_aligned_words(aligned, plan=plan)


# =====================================================
# CAPTION BUILDING
# =====================================================


def _make_word_clip(
    text,
    font,
    font_size,
    color,
    stroke_width=CAPTION_STROKE,
):
    """Create one tight MoviePy 2.x word label."""
    kwargs = {
        "text": text.upper(),
        "font_size": int(font_size),
        "color": color,
        "stroke_color": "black",
        "stroke_width": int(stroke_width),
        "method": "label",
        "text_align": "center",
        "horizontal_align": "center",
        "vertical_align": "center",
        "transparent": True,
    }

    if font:
        kwargs["font"] = font

    return TextClip(**kwargs)


def _calculate_font_size(words, font, preferred=CAPTION_FONT_SIZE):
    """Shrink the font only when needed to keep a caption group centered and readable."""
    size = preferred

    while size >= CAPTION_MIN_FONT_SIZE:
        measured = []
        total_width = 0

        for word in words:
            probe = _make_word_clip(word["word"], font, size, DEFAULT_NORMAL)
            try:
                measured.append((probe.w, probe.h))
                total_width += probe.w
            finally:
                safe_close(probe)

        total_width += max(0, len(words) - 1) * CAPTION_SPACING

        if total_width <= CAPTION_MAX_WIDTH:
            return size, measured

        size -= 4

    measured = []
    total_width = 0
    for word in words:
        probe = _make_word_clip(
            word["word"],
            font,
            CAPTION_MIN_FONT_SIZE,
            DEFAULT_NORMAL,
        )
        try:
            measured.append((probe.w, probe.h))
            total_width += probe.w
        finally:
            safe_close(probe)

    return CAPTION_MIN_FONT_SIZE, measured


def _active_color(word):
    style = str(word.get("style", "normal")).lower()
    supplied = str(word.get("color", "")).strip()

    if supplied and supplied.lower() not in {"#ffffff", "white"}:
        return supplied

    if style == "pain":
        return DEFAULT_PAIN
    if style == "hope":
        return DEFAULT_HOPE
    return DEFAULT_HIGHLIGHT


def _is_power_word(word):
    return str(word.get("animation", "")).lower() == "impact_pop" or str(
        word.get("style", "")
    ).lower() in {"highlight", "pain", "hope"}


def make_caption_group(group, font):
    """Create a centered caption group with active-word overlays."""
    words = group.get("words", [])
    if not words:
        return []

    font_size, measured = _calculate_font_size(words, font)

    total_width = (
        sum(width for width, _ in measured)
        + max(0, len(words) - 1) * CAPTION_SPACING
    )

    left = CAPTION_CENTER_X - total_width / 2
    max_height = max(height for _, height in measured)
    top = CAPTION_CENTER_Y - max_height / 2

    clips = []
    x_positions = []

    x = left
    for width, _ in measured:
        x_positions.append(x)
        x += width + CAPTION_SPACING

    group_start = float(group["start"])
    group_end = float(group["end"])
    group_duration = max(0.05, group_end - group_start)

    # Base sentence: all words remain visible together.
    for index, word in enumerate(words):
        base = _make_word_clip(
            word["word"],
            font,
            font_size,
            DEFAULT_NORMAL,
        )
        base = (
            base.with_position((x_positions[index], top))
            .with_start(group_start)
            .with_duration(group_duration)
        )
        clips.append(base)

    # Active spoken word: color change + optional short power-word pop.
    for index, word in enumerate(words):
        start = max(group_start, float(word["start"]))
        end = min(group_end, float(word["end"]))
        duration = end - start

        if duration <= 0:
            continue

        active = _make_word_clip(
            word["word"],
            font,
            font_size,
            _active_color(word),
        )

        active = (
            active.with_position((x_positions[index], top))
            .with_start(start)
            .with_duration(duration)
        )
        clips.append(active)

        # Small scale pop for high-impact words, not every word.
        if _is_power_word(word):
            pop_end = min(end, start + CAPTION_POP_DURATION)
            pop_duration = pop_end - start

            if pop_duration > 0:
                pop_size = min(font_size + 12, font_size * 1.14)
                pop = _make_word_clip(
                    word["word"],
                    font,
                    pop_size,
                    _active_color(word),
                )

                center_x = x_positions[index] + measured[index][0] / 2
                center_y = top + max_height / 2
                pop_x = center_x - pop.w / 2
                pop_y = center_y - pop.h / 2

                pop = (
                    pop.with_position((pop_x, pop_y))
                    .with_start(start)
                    .with_duration(pop_duration)
                )
                clips.append(pop)

    return clips


def make_caption(text, start, end):
    """Backward-compatible single-caption fallback using MoviePy 2.x syntax."""
    duration = max(0.4, end - start)
    font = resolve_caption_font("montserrat")

    kwargs = {
        "text": str(text).upper(),
        "font_size": 84,
        "color": DEFAULT_NORMAL,
        "stroke_color": "black",
        "stroke_width": CAPTION_STROKE,
        "method": "caption",
        "size": (CAPTION_MAX_WIDTH, None),
        "text_align": "center",
        "horizontal_align": "center",
        "vertical_align": "center",
        "transparent": True,
    }

    if font:
        kwargs["font"] = font

    txt = TextClip(**kwargs)

    return (
        txt.with_position(("center", "center"))
        .with_start(start)
        .with_duration(duration)
    )


def build_captions(narration):
    audio = OUTPUT / "voice.wav"

    if not audio.exists():
        return []

    plan = load_caption_plan()
    plan = _rebuild_plan_timing(plan, narration, audio)

    if plan:
        theme = choose_caption_theme(narration, plan)
        font = resolve_caption_font(theme)

        print(
            "Caption style:",
            theme,
            "font:",
            font or "MoviePy/default",
        )

        clips = []
        for group in plan:
            clips.extend(make_caption_group(group, font))

        if clips:
            return clips

    # Final fallback for unusual runs where no aligned caption plan can be made.
    timings = caption_segments(audio, narration)

    if timings:
        fallback_groups = _groups_from_aligned_words(timings, plan=None)
        theme = choose_caption_theme(narration, None)
        font = resolve_caption_font(theme)
        clips = []
        for group in fallback_groups:
            clips.extend(make_caption_group(group, font))
        if clips:
            return clips

    return [make_caption(narration, 0, get_audio_duration())]


# =====================================================
# SUCCESSFUL-RENDER CLEANUP
# =====================================================


def cleanup_temporary_assets():
    """
    Remove only large renderer-generated source media.

    Important small deliverables such as caption_plan.json, production data,
    generation history, voice.wav, and final_short.mp4 are intentionally kept.
    """
    removed = []

    for pattern in TEMP_ASSET_PATTERNS:
        for path in OUTPUT.glob(pattern):
            if not path.is_file():
                continue

            try:
                size = path.stat().st_size
                path.unlink()
                removed.append((path.name, size))
            except Exception as exc:
                print("Could not remove temporary asset:", path, exc)

    if removed:
        total_mb = sum(size for _, size in removed) / (1024 * 1024)
        print(
            f"Cleaned {len(removed)} temporary asset(s) "
            f"({total_mb:.1f} MB)."
        )
    else:
        print("No temporary media assets required cleanup.")


# =====================================================
# RENDER
# =====================================================


def render():
    print("V6.1 Premium Renderer Starting")

    brief = load_json(OUTPUT / "production_brief.json")
    assets = load_json(OUTPUT / "visual_assets.json")

    total = get_audio_duration()

    scene_count = len(brief.get("scenes", []))
    duration = total / max(scene_count, 1)

    clips = []
    caption_clips = []
    video = None
    voice = None
    final = None
    render_succeeded = False

    try:
        for scene in brief.get("scenes", []):
            group = next(
                (
                    x for x in assets.get("videos", [])
                    if x.get("scene") == scene.get("scene")
                ),
                {},
            )

            candidates = group.get("videos", [])
            asset = candidates[0] if candidates else None

            clips.append(create_visual(asset, duration))

        video = concatenate_videoclips(
            clips,
            method="compose",
        )

        if (OUTPUT / "voice.wav").exists():
            voice = AudioFileClip(str(OUTPUT / "voice.wav"))
            video = video.with_audio(
                CompositeAudioClip([voice])
            )

        caption_clips = build_captions(brief.get("narration", ""))

        final = CompositeVideoClip(
            [video] + caption_clips,
            size=(WIDTH, HEIGHT),
        )

        final.write_videofile(
            str(FINAL_VIDEO),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
        )

        render_succeeded = FINAL_VIDEO.exists() and FINAL_VIDEO.stat().st_size > 0

        if render_succeeded:
            print("DONE:", FINAL_VIDEO)

    finally:
        # Close output/composite objects before deleting any source assets.
        safe_close(final)
        safe_close(voice)
        safe_close(video)

        for clip in caption_clips:
            safe_close(clip)

        for clip in clips:
            safe_close(clip)

        if render_succeeded:
            cleanup_temporary_assets()
        else:
            print(
                "Render did not complete successfully; temporary assets "
                "were kept for debugging/retry."
            )

    return render_succeeded


if __name__ == "__main__":
    render()

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
CAPTION_MIN_FONT_SIZE = 68
CAPTION_FONT_SIZE = 88
CAPTION_STROKE = 6
CAPTION_SPACING = 14
CAPTION_LINE_SPACING = 8
CAPTION_CENTER_X = WIDTH / 2

# Keep captions centered inside a conservative Shorts/Reels/TikTok safe area.
CAPTION_SAFE_TOP = 220
CAPTION_SAFE_BOTTOM = 320
CAPTION_SAFE_LEFT = 60
CAPTION_SAFE_RIGHT = 60
CAPTION_SAFE_CENTER_Y = (CAPTION_SAFE_TOP + (HEIGHT - CAPTION_SAFE_BOTTOM)) / 2
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


def fit_vertical(clip, focus_x=0.5, focus_y=0.5):
    """Fit media to 1080x1920 with a controlled crop focus.

    The default remains a centered crop. Reused assets may receive a small,
    deterministic focus shift so returning footage does not look like a
    copy-pasted loop.
    """
    clip = clip.resized(height=HEIGHT)

    if clip.w < WIDTH:
        clip = clip.resized(width=WIDTH)

    focus_x = max(0.0, min(1.0, float(focus_x)))
    focus_y = max(0.0, min(1.0, float(focus_y)))

    x_center = (clip.w - WIDTH) * focus_x + WIDTH / 2
    y_center = (clip.h - HEIGHT) * focus_y + HEIGHT / 2

    # MoviePy 2.x renamed crop -> cropped
    if hasattr(clip, "cropped"):
        return clip.cropped(
            x_center=x_center,
            y_center=y_center,
            width=WIDTH,
            height=HEIGHT,
        )

    return clip.crop(
        x_center=x_center,
        y_center=y_center,
        width=WIDTH,
        height=HEIGHT,
    )


def cinematic_grade(clip, intensity=0.42):
    intensity = max(0.0, min(0.55, float(intensity)))
    overlay = ColorClip(
        (WIDTH, HEIGHT),
        color=(0, 0, 0),
        duration=clip.duration,
    ).with_opacity(intensity)

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


def create_visual(asset, duration, scene_index=1, reuse_variant=0, grade_strength=0.42):
    """Create one visual while allowing deliberate crop/timing variation on reuse."""
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

    # Slight deterministic crop variation is only used when an asset returns.
    # First use stays centered; later uses shift subtly left/right.
    variant = int(reuse_variant or 0)
    focus_options = (0.50, 0.44, 0.56)
    focus_x = focus_options[variant % len(focus_options)]
    focus_y = 0.50

    if is_video:
        clip = VideoFileClip(str(path))
        if clip.duration > duration:
            max_start = max(0.0, clip.duration - duration)
            # Deterministic excerpt variation; no random behaviour.
            start_offset = min(
                max_start,
                (scene_index * 1.37 + variant * 2.11) % (max_start + 0.01),
            )
            clip = clip.subclipped(start_offset, start_offset + duration)
    else:
        clip = ImageClip(str(path)).with_duration(duration)

    return cinematic_grade(
        fit_vertical(clip, focus_x=focus_x, focus_y=focus_y),
        intensity=grade_strength,
    )



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
    """Resolve a story-appropriate display font with robust runner fallbacks."""
    exact = {
        "montserrat": [
            "montserrat-extrabold",
            "montserrat-black",
            "montserrat-bold",
        ],
        "anton": [
            "anton-regular",
            "anton",
            "oswald-bold",
            "bebasneue",
        ],
        "impact": [
            "impact",
            "anton",
            "oswald-bold",
        ],
        "sfpro": [
            "sf-pro-display-bold",
            "sfprodisplay-bold",
            "sfprodisplay",
            "interdisplay-bold",
            "inter-bold",
        ],
        "classical": [
            "ebgaramond12-bold",
            "ebgaramond-bold",
            "cormorantgaramond-bold",
            "cinzel-bold",
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
            "/usr/share/fonts/truetype/liberation/LiberationSansNarrow-Bold.ttf",
        ],
        "impact": [
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
        ],
        "sfpro": [
            "/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf",
            "/usr/share/fonts/opentype/inter/Inter-Bold.otf",
            "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ],
        "classical": [
            "/usr/share/fonts/truetype/ebgaramond/EBGaramond12-Bold.ttf",
            "/usr/share/fonts/truetype/ebgaramond/EBGaramond-InitialsF1.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        ],
        "helvetica": [
            "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf",
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


def choose_caption_theme(narration, caption_plan=None, brief=None):
    """Pick one intentional typography personality for the whole video."""
    text_parts = [str(narration or "")]

    if isinstance(brief, dict):
        text_parts.extend(
            [
                str(brief.get("title", "")),
                str(brief.get("theme", "")),
                str(brief.get("voice_direction", {}).get("personality", "")),
                str(brief.get("creative_direction", {}).get("philosophical_theme", "")),
                str(brief.get("creative_direction", {}).get("emotional_arc", "")),
                str(brief.get("creative_direction", {}).get("visual_style", "")),
            ]
        )

    text = " ".join(text_parts).lower()

    scores = {
        "montserrat": 0,
        "anton": 0,
        "impact": 0,
        "sfpro": 0,
        "classical": 0,
        "helvetica": 0,
    }

    keyword_sets = {
        "anton": {
            "warrior", "battle", "fight", "grind", "discipline",
            "sacrifice", "challenge", "prove", "strong", "strength",
            "pain", "failure", "comeback", "rise", "resilience",
            "self-mastery", "mastery", "unstoppable", "win", "never",
        },
        "impact": {
            "fear", "broken", "lost", "alone", "regret", "warning",
            "danger", "truth", "wake", "destroy", "failure", "stop",
            "crisis", "hard", "pain",
        },
        "montserrat": {
            "success", "business", "work", "career", "money", "wealth",
            "focus", "productivity", "goal", "growth", "confidence",
            "achievement", "discipline", "performance", "success",
        },
        "sfpro": {
            "life", "future", "purpose", "meaning", "mind", "choice",
            "time", "today", "tomorrow", "believe", "thought",
            "journey", "identity", "calm", "healing", "reflection",
        },
        "classical": {
            "stoic", "stoicism", "marcus", "aurelius", "seneca",
            "epictetus", "ancient", "wisdom", "philosophy", "virtue",
            "roman", "ethics", "self-control", "self control",
        },
        "helvetica": {
            "premium", "modern", "clean", "minimal", "clarity",
            "clarity", "technology", "modern", "precision",
        },
    }

    for theme, words in keyword_sets.items():
        for word in words:
            if re.search(rf"\b{re.escape(word)}\b", text):
                scores[theme] += 2

    if isinstance(brief, dict):
        voice = str(brief.get("voice_direction", {}).get("personality", "")).lower()
        if "stoic" in voice:
            scores["classical"] += 5
        elif "power" in voice:
            scores["anton"] += 4
        elif "warm" in voice:
            scores["sfpro"] += 3
        elif "hopeful" in voice:
            scores["montserrat"] += 2

    if caption_plan:
        styled = [
            word
            for item in caption_plan
            for word in item.get("words", [])
        ]
        hope_count = sum(
            1
            for word in styled
            if str(word.get("style", "")).lower() == "hope"
        )
        pain_count = sum(
            1
            for word in styled
            if str(word.get("style", "")).lower() == "pain"
        )
        if hope_count >= 2:
            scores["sfpro"] += 2
        if pain_count >= 2:
            scores["impact"] += 2

    # Keep one coherent typography personality throughout a video.
    best = max(scores, key=scores.get)
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


def _measure_words(words, font, font_size):
    measured = []
    for word in words:
        probe = _make_word_clip(
            word["word"],
            font,
            font_size,
            DEFAULT_NORMAL,
        )
        try:
            measured.append((probe.w, probe.h))
        finally:
            safe_close(probe)
    return measured


def _wrap_caption_words(words, measured, max_width):
    """Greedy 1-2 line wrap, preserving word order and timings."""
    lines = []
    current = []
    current_width = 0

    for index, (word, size) in enumerate(zip(words, measured)):
        width = size[0]
        proposed = width if not current else current_width + CAPTION_SPACING + width

        if current and proposed > max_width:
            lines.append(current)
            current = [index]
            current_width = width
        else:
            current.append(index)
            current_width = proposed

    if current:
        lines.append(current)

    return lines


def _calculate_caption_layout(words, font, preferred=CAPTION_FONT_SIZE):
    """Find the largest readable size that fits inside the safe width in <=2 lines."""
    size = preferred

    while size >= CAPTION_MIN_FONT_SIZE:
        measured = _measure_words(words, font, size)
        lines = _wrap_caption_words(words, measured, CAPTION_MAX_WIDTH)

        if len(lines) <= 2:
            return size, measured, lines

        size -= 4

    measured = _measure_words(words, font, CAPTION_MIN_FONT_SIZE)
    lines = _wrap_caption_words(words, measured, CAPTION_MAX_WIDTH)
    return CAPTION_MIN_FONT_SIZE, measured, lines[:2]


def _clamp_caption_position(x, y, width, height):
    left_limit = CAPTION_SAFE_LEFT
    right_limit = WIDTH - CAPTION_SAFE_RIGHT - width
    top_limit = CAPTION_SAFE_TOP
    bottom_limit = HEIGHT - CAPTION_SAFE_BOTTOM - height

    return (
        max(left_limit, min(float(x), float(right_limit))),
        max(top_limit, min(float(y), float(bottom_limit))),
    )


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
    """Create a centered caption group with safe-area layout and active-word overlays."""
    words = group.get("words", [])
    if not words:
        return []

    font_size, measured, lines = _calculate_caption_layout(words, font)

    line_widths = []
    line_heights = []
    for line in lines:
        line_widths.append(
            sum(measured[i][0] for i in line)
            + max(0, len(line) - 1) * CAPTION_SPACING
        )
        line_heights.append(max(measured[i][1] for i in line))

    total_height = sum(line_heights) + max(0, len(lines) - 1) * CAPTION_LINE_SPACING
    top = CAPTION_SAFE_CENTER_Y - total_height / 2
    top = max(
        CAPTION_SAFE_TOP,
        min(top, HEIGHT - CAPTION_SAFE_BOTTOM - total_height),
    )

    positions = {}
    current_y = top

    for line_index, line in enumerate(lines):
        line_width = line_widths[line_index]
        x = CAPTION_CENTER_X - line_width / 2
        line_height = line_heights[line_index]

        for word_index in line:
            word_width, word_height = measured[word_index]
            y = current_y + (line_height - word_height) / 2
            x, y = _clamp_caption_position(x, y, word_width, word_height)
            positions[word_index] = (x, y)
            x += word_width + CAPTION_SPACING

        current_y += line_height + CAPTION_LINE_SPACING

    group_start = float(group["start"])
    group_end = float(group["end"])
    group_duration = max(0.05, group_end - group_start)

    clips = []

    # Base sentence: all words remain visible together.
    for index, word in enumerate(words):
        base = _make_word_clip(
            word["word"],
            font,
            font_size,
            DEFAULT_NORMAL,
        )
        x, y = positions[index]
        base = (
            base.with_position((x, y))
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

        x, y = positions[index]
        active = (
            active.with_position((x, y))
            .with_start(start)
            .with_duration(duration)
        )
        clips.append(active)

        if _is_power_word(word):
            pop_end = min(end, start + CAPTION_POP_DURATION)
            pop_duration = pop_end - start

            if pop_duration > 0:
                pop_size = min(font_size + 12, int(font_size * 1.14))
                pop = _make_word_clip(
                    word["word"],
                    font,
                    pop_size,
                    _active_color(word),
                )

                center_x = x + measured[index][0] / 2
                center_y = y + measured[index][1] / 2
                pop_x = center_x - pop.w / 2
                pop_y = center_y - pop.h / 2
                pop_x, pop_y = _clamp_caption_position(pop_x, pop_y, pop.w, pop.h)

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
        txt.with_position(("center", CAPTION_SAFE_CENTER_Y))
        .with_start(start)
        .with_duration(duration)
    )


def build_captions(narration, brief=None):
    audio = OUTPUT / "voice.wav"

    if not audio.exists():
        return []

    plan = load_caption_plan()
    plan = _rebuild_plan_timing(plan, narration, audio)

    if plan:
        theme = choose_caption_theme(narration, plan, brief=brief)
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
        theme = choose_caption_theme(narration, None, brief=brief)
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
# SMART VISUAL SELECTION
# =====================================================


def _tokenize_visual_text(value):
    return {
        token
        for token in re.findall(r"[a-z0-9']+", str(value or "").lower())
        if len(token) >= 3
    }


def _visual_text(scene):
    visual = scene.get("visual", {}) if isinstance(scene, dict) else {}
    return " ".join(
        [
            str(scene.get("pexels_query", "")),
            str(scene.get("caption", "")),
            str(scene.get("voice_line", "")),
            str(visual.get("type", "")),
            str(visual.get("subject", "")),
            str(visual.get("action", "")),
            str(visual.get("emotion", "")),
            str(visual.get("environment", "")),
            str(visual.get("composition", "")),
            str(visual.get("camera", "")),
        ]
    )


def _asset_text(asset):
    return " ".join(
        [
            str(asset.get("url", "")),
            str(asset.get("preview", "")),
            str(asset.get("alt", "")),
            str(asset.get("image", "")),
            str(asset.get("video_file", "")),
        ]
    )


def _source_kind(asset):
    return "video" if asset and asset.get("video_file") else "image"


def _story_prefers_video(scene):
    visual = scene.get("visual", {}) if isinstance(scene, dict) else {}
    text = _visual_text(scene).lower()
    dynamic_words = {
        "walk", "walking", "run", "running", "fight", "fighting",
        "train", "training", "climb", "fall", "rising", "rise",
        "open", "opening", "turn", "turning", "break", "breaking",
        "move", "moving", "drive", "driving", "work", "working",
        "swing", "sprinting", "storm", "wave", "waves", "motion",
    }
    type_text = str(visual.get("type", "")).lower()
    camera_text = str(visual.get("camera", "")).lower()

    dynamic_score = sum(1 for word in dynamic_words if re.search(rf"\b{re.escape(word)}\b", text))
    if any(term in type_text for term in ("wide", "action", "tracking", "motion", "slow-motion")):
        dynamic_score += 2
    if any(term in camera_text for term in ("tracking", "pan", "dolly", "movement", "slow-motion")):
        dynamic_score += 2
    return dynamic_score >= 2


def _story_prefers_image(scene):
    visual = scene.get("visual", {}) if isinstance(scene, dict) else {}
    text = _visual_text(scene).lower()
    static_terms = {
        "statue", "manuscript", "book", "candle", "key", "sword",
        "portrait", "reflection", "shadow", "silhouette", "ruins",
        "architecture", "marble", "letter", "photograph", "symbol",
        "hourglass", "artwork", "painting", "still", "detail",
    }
    type_text = str(visual.get("type", "")).lower()
    score = sum(1 for word in static_terms if re.search(rf"\b{re.escape(word)}\b", text))
    if any(term in type_text for term in ("detail", "close-up", "close up", "symbolic", "portrait", "still")):
        score += 2
    return score >= 2


def _asset_score(asset, scene, target_duration, state):
    kind = _source_kind(asset)
    story_tokens = _tokenize_visual_text(_visual_text(scene))
    asset_tokens = _tokenize_visual_text(_asset_text(asset))
    overlap = len(story_tokens & asset_tokens)
    score = overlap * 3.5

    if _story_prefers_video(scene):
        score += 18 if kind == "video" else 4
    elif _story_prefers_image(scene):
        score += 18 if kind == "image" else 5
    else:
        score += 9

    if kind == "video":
        width = float(asset.get("video_file_width") or asset.get("width") or 0)
        height = float(asset.get("video_file_height") or asset.get("height") or 0)
        duration = float(asset.get("duration") or 0)
        if width >= 1920 and height >= 1080:
            score += 5
        if duration >= target_duration:
            score += 5
        elif duration >= target_duration * 0.75:
            score += 2
    else:
        width = float(asset.get("width") or 0)
        height = float(asset.get("height") or 0)
        if width >= 1920 and height >= 1080:
            score += 5

    key = (kind, str(asset.get("id", "")))
    used_count = int(state.get("used", {}).get(key, 0))
    if used_count == 0:
        score += 8
    elif used_count == 1:
        # Intentional reuse is allowed when a strong candidate returns.
        if key != state.get("last_key"):
            score += 7
        else:
            score -= 18
    else:
        score -= 60

    if key == state.get("last_key"):
        score -= 45

    return score


def choose_visual_asset(scene, assets, target_duration, state):
    """Choose video/image from the already-collected Pexels candidates."""
    scene_no = scene.get("scene")
    video_group = next(
        (item for item in assets.get("videos", []) if item.get("scene") == scene_no),
        {},
    )
    image_group = next(
        (item for item in assets.get("images", []) if item.get("scene") == scene_no),
        {},
    )

    candidates = []
    for item in video_group.get("videos", []) or []:
        candidate = dict(item)
        candidate["_kind"] = "video"
        candidates.append(candidate)
    for item in image_group.get("images", []) or []:
        candidate = dict(item)
        candidate["_kind"] = "image"
        candidates.append(candidate)

    if not candidates:
        return None, 0

    scored = [
        (_asset_score(candidate, scene, target_duration, state), candidate)
        for candidate in candidates
    ]
    scored.sort(key=lambda item: item[0], reverse=True)

    score, selected = scored[0]
    key = (_source_kind(selected), str(selected.get("id", "")))
    reuse_variant = int(state.get("used", {}).get(key, 0))
    state.setdefault("used", {})[key] = reuse_variant + 1
    state["last_key"] = key
    state.setdefault("history", []).append(
        {
            "scene": scene_no,
            "kind": _source_kind(selected),
            "id": selected.get("id"),
            "score": round(score, 2),
            "reuse": reuse_variant,
        }
    )

    return selected, reuse_variant


# =====================================================
# SEO METADATA
# =====================================================


SEO_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into",
    "your", "you", "our", "are", "not", "but", "what", "when",
    "how", "why", "can", "will", "its", "about", "than", "have",
    "has", "been", "being", "their", "they", "them", "all", "one",
    "just", "like", "through", "after", "before", "over", "under",
}


def _seo_words(text):
    words = []
    for token in re.findall(r"[A-Za-z][A-Za-z0-9-]+", str(text or "")):
        clean = token.lower().strip("-")
        if len(clean) >= 4 and clean not in SEO_STOPWORDS and clean not in words:
            words.append(clean)
    return words


def build_seo_metadata(brief):
    """Create natural topic-based metadata without changing story generation."""
    title = str(brief.get("title", "Motivational Short")).strip()
    theme = str(brief.get("theme", "")).strip()
    hook = str(brief.get("hook", "")).strip()
    narration = str(brief.get("narration", "")).strip()
    creative = brief.get("creative_direction", {}) or {}
    scenes = brief.get("scenes", []) or []

    scene_topics = []
    for scene in scenes:
        scene_topics.extend(
            [
                str(scene.get("caption", "")),
                str(scene.get("pexels_query", "")),
                str(scene.get("visual", {}).get("subject", "")),
            ]
        )

    raw_terms = _seo_words(
        " ".join(
            [
                title,
                theme,
                str(creative.get("philosophical_theme", "")),
                str(creative.get("emotional_arc", "")),
                *scene_topics,
            ]
        )
    )

    # Keep keywords focused rather than dumping every narration word.
    keywords = raw_terms[:14]

    hashtags = []
    for term in keywords:
        tag = "#" + re.sub(r"[^A-Za-z0-9]", "", term.title())
        if tag not in hashtags:
            hashtags.append(tag)
        if len(hashtags) >= 8:
            break

    description_parts = []
    if hook:
        description_parts.append(hook)
    if theme:
        description_parts.append(
            f"A cinematic motivational short about {theme.lower()}, resilience, and personal growth."
        )
    if narration:
        sentences = re.split(r"(?<=[.!?])\s+", narration)
        summary = " ".join(sentences[:2]).strip()
        if summary and summary != hook:
            description_parts.append(summary)

    description = " ".join(description_parts).strip()
    if len(description) > 4200:
        description = description[:4197].rsplit(" ", 1)[0] + "..."

    return {
        "title": title,
        "description": description,
        "keywords": keywords,
        "hashtags": hashtags,
        "topic": theme,
        "source": "generated from production_brief.json without changing the content pipeline",
    }


def save_seo_metadata(brief):
    metadata = build_seo_metadata(brief)
    with open(OUTPUT / "seo_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(
        "SEO metadata saved:",
        metadata.get("title", ""),
    )


# =====================================================
# RENDER
# =====================================================


def render():
    print("V6.1 Premium Renderer Starting")

    brief = load_json(OUTPUT / "production_brief.json")
    assets = load_json(OUTPUT / "visual_assets.json")

    total = get_audio_duration()

    save_seo_metadata(brief)

    scene_count = len(brief.get("scenes", []))
    duration = total / max(scene_count, 1)

    clips = []
    caption_clips = []
    video = None
    voice = None
    final = None
    render_succeeded = False

    try:
        selection_state = {"used": {}, "last_key": None, "history": []}

        for scene in brief.get("scenes", []):
            asset, reuse_variant = choose_visual_asset(
                scene,
                assets,
                duration,
                selection_state,
            )

            if asset:
                print(
                    f"Scene {scene.get('scene')}: "
                    f"{_source_kind(asset)} asset {asset.get('id')} "
                    f"(reuse={reuse_variant})"
                )
            else:
                print(
                    f"Scene {scene.get('scene')}: no suitable asset found; "
                    "using fallback background."
                )

            # Slightly stronger treatment for darker/pain-oriented beats, and
            # slightly lighter treatment for hopeful beats. This keeps the
            # story's visual arc without changing the underlying scene logic.
            emotion = str(scene.get("visual", {}).get("emotion", "")).lower()
            grade_strength = 0.42
            if any(word in emotion for word in ("hope", "inspiration", "confidence", "determination")):
                grade_strength = 0.34
            elif any(word in emotion for word in ("despair", "hopeless", "pain", "fear", "dark")):
                grade_strength = 0.47

            clips.append(
                create_visual(
                    asset,
                    duration,
                    scene_index=int(scene.get("scene") or 1),
                    reuse_variant=reuse_variant,
                    grade_strength=grade_strength,
                )
            )

        video = concatenate_videoclips(
            clips,
            method="compose",
        )

        if (OUTPUT / "voice.wav").exists():
            voice = AudioFileClip(str(OUTPUT / "voice.wav"))
            video = video.with_audio(
                CompositeAudioClip([voice])
            )

        caption_clips = build_captions(brief.get("narration", ""), brief=brief)

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

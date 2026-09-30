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

# Keep captions comfortably inside the horizontal Shorts safe area.
CAPTION_MAX_WIDTH = 940
CAPTION_SAFE_LEFT = 70
CAPTION_SAFE_RIGHT = 70
CAPTION_MIN_FONT_SIZE = 60
CAPTION_FONT_SIZE = 84
CAPTION_STROKE = 6
CAPTION_MARGIN = 4
CAPTION_LINE_GAP = 8
# Extra internal vertical room prevents font/stroke rasterization from clipping
# the lower edge of glyphs. Horizontal spacing/visual font size stay unchanged.
CAPTION_VERTICAL_MARGIN = 24
CAPTION_SPACING = 10
CAPTION_CENTER_X = WIDTH / 2
# Keep the existing visual position, but clamp the full text/stroke bounding box
# inside a dedicated vertical safe area so glyphs/borders cannot be cropped.
CAPTION_SAFE_TOP = 720
CAPTION_SAFE_BOTTOM = 1200
CAPTION_CENTER_Y = (CAPTION_SAFE_TOP + CAPTION_SAFE_BOTTOM) / 2
CAPTION_POP_DURATION = 0.11

# Existing caption-plan colors are preserved.
DEFAULT_NORMAL = "#FFFFFF"
DEFAULT_HIGHLIGHT = "#FFD447"
DEFAULT_PAIN = "#FF5555"
DEFAULT_HOPE = "#45E6FF"

# Controlled premium accents. These are semantic, not random, so a whole
# video keeps a coherent visual identity instead of becoming rainbow text.
PREMIUM_ACCENTS = {
    "success": "#FFD447",
    "discipline": "#FFB14A",
    "courage": "#FF6B57",
    "hope": "#55DDF5",
    "vision": "#B68CFF",
    "growth": "#67D98C",
    "struggle": "#FF5B62",
    "time": "#FFC857",
}

PREMIUM_KEYWORDS = {
    "success": {
        "success", "successful", "win", "winner", "winning", "victory",
        "achieve", "achieved", "achievement", "excel", "excellence",
        "result", "results", "champion", "mastery", "breakthrough",
    },
    "discipline": {
        "discipline", "focus", "control", "consistency", "consistent",
        "determination", "determined", "persistence", "persistent",
        "sacrifice", "action", "effort", "work", "grind", "commit",
        "commitment", "patience",
    },
    "courage": {
        "courage", "brave", "bravery", "fearless", "fearlessness",
        "strength", "strong", "power", "powerful", "warrior", "conquer",
        "conquered", "rise", "rising", "resilience", "resilient",
    },
    "hope": {
        "hope", "faith", "believe", "belief", "believed", "future",
        "light", "heal", "healing", "renew", "renewal", "peace",
    },
    "vision": {
        "dream", "dreams", "vision", "purpose", "ambition", "potential",
        "opportunity", "freedom", "leadership", "mindset", "purposeful",
        "transform", "transformation", "become", "becoming",
    },
    "growth": {
        "grow", "growth", "progress", "progression", "improve",
        "improvement", "change", "changing", "rise", "rising", "evolve",
        "evolution", "learn", "learning",
    },
    "struggle": {
        "pain", "struggle", "struggles", "failure", "failed", "fail",
        "hurt", "broken", "loss", "lost", "doubt", "doubts", "fear",
        "obstacle", "obstacles", "hardship", "suffering",
    },
    "time": {
        "time", "moment", "now", "today", "tomorrow", "seconds",
        "minute", "minutes", "day", "days", "season", "wait", "waiting",
    },
}

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


def fit_vertical(clip, focus_x=0.5, zoom=1.0):
    """Fit landscape media into 9:16 with a small, scene-aware crop bias."""
    zoom = max(1.0, float(zoom))
    focus_x = min(1.0, max(0.0, float(focus_x)))

    clip = clip.resized(height=HEIGHT * zoom)

    if clip.w < WIDTH:
        clip = clip.resized(width=WIDTH)

    x_center = clip.w * focus_x
    half_width = WIDTH / 2
    x_center = min(max(half_width, x_center), clip.w - half_width)

    # MoviePy 2.x renamed crop -> cropped
    if hasattr(clip, "cropped"):
        return clip.cropped(
            x_center=x_center,
            y_center=clip.h / 2,
            width=WIDTH,
            height=HEIGHT,
        )

    return clip.crop(
        x_center=x_center,
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


def create_visual(asset, duration, focus_x=0.5, zoom=1.0):
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

    return cinematic_grade(fit_vertical(clip, focus_x=focus_x, zoom=zoom))


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

    # Preserve the caller's preference order instead of returning whichever
    # matching font happens to appear first in a filesystem traversal.
    for token in wanted:
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
                if token in name:
                    return str(candidate)

    return None


def resolve_caption_font(theme):
    """Resolve one intentional whole-video font family from installed fonts."""
    exact = {
        "warrior": [
            "InterDisplay-ExtraBold",
            "Inter-Black",
            "Lato-Heavy",
        ],
        "stoic": [
            "EBGaramond12-Bold",
            "EBGaramond12-Regular",
            "DejaVuSerifCondensed-Bold",
        ],
        "cinematic": [
            "Lato-Black",
            "Inter-SemiBold",
            "InterDisplay-SemiBold",
        ],
        "calm": [
            "InterDisplay-SemiBold",
            "Inter-SemiBold",
            "Lato-Bold",
        ],
        # Backward-compatible theme names.
        "montserrat": [
            "InterDisplay-ExtraBold",
            "Lato-Black",
        ],
        "anton": [
            "InterDisplay-ExtraBold",
            "DejaVuSansCondensed-Bold",
        ],
        "impact": [
            "Inter-Black",
            "Lato-Heavy",
        ],
        "sfpro": [
            "InterDisplay-SemiBold",
            "Lato-Heavy",
        ],
        "helvetica": [
            "Inter-SemiBold",
            "LiberationSans-Bold",
        ],
    }

    fallbacks = {
        "warrior": [
            "/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf",
            "/usr/share/fonts/truetype/lato/Lato-Heavy.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        ],
        "stoic": [
            "/usr/share/fonts/truetype/ebgaramond/EBGaramond12-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerifCondensed-Bold.ttf",
        ],
        "cinematic": [
            "/usr/share/fonts/truetype/lato/Lato-Black.ttf",
            "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf",
        ],
        "calm": [
            "/usr/share/fonts/opentype/inter/InterDisplay-SemiBold.otf",
            "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
        ],
    }

    exact_path = _find_font_file(exact.get(theme, []))
    if exact_path:
        return exact_path

    for fallback in fallbacks.get(theme, []) + fallbacks.get("cinematic", []):
        if Path(fallback).exists():
            return fallback

    return None


def choose_caption_theme(narration, caption_plan=None, brief=None):
    """Choose one deterministic caption personality for the entire video."""
    text_parts = [str(narration or "").lower()]
    if isinstance(brief, dict):
        creative = brief.get("creative_direction", {}) or {}
        voice = brief.get("voice_direction", {}) or {}
        text_parts.extend(str(creative.get(key, "")).lower() for key in (
            "philosophical_theme", "emotional_arc", "visual_style", "color_mood"
        ))
        text_parts.extend(str(voice.get(key, "")).lower() for key in (
            "personality", "emotion", "intensity", "pace"
        ))

    text = " ".join(text_parts)

    themes = {
        "warrior": {
            "never", "quit", "fight", "hard", "grind", "discipline",
            "sacrifice", "challenge", "prove", "strong", "strength",
            "pain", "failure", "comeback", "rise", "battle", "win",
            "warrior", "resilience", "determined", "intensity", "power",
        },
        "stoic": {
            "marcus", "aurelius", "stoic", "stoicism", "philosophy",
            "wisdom", "self-control", "self mastery", "mastery", "purpose",
            "meaning", "ancient", "classical", "reflection", "discipline",
        },
        "cinematic": {
            "loss", "broken", "healing", "emotional", "heart", "lonely",
            "isolation", "grief", "regret", "hope", "transformation",
            "cinematic", "melancholic", "empathetic",
        },
        "calm": {
            "life", "future", "mind", "choice", "time", "today",
            "tomorrow", "believe", "thought", "journey", "identity",
            "calm", "reflective", "gentle", "peace",
        },
    }

    scores = {
        theme: sum(1 for keyword in keywords if re.search(rf"\b{re.escape(keyword)}\b", text))
        for theme, keywords in themes.items()
    }

    if isinstance(brief, dict):
        voice_personality = str(
            brief.get("voice_direction", {}).get("personality", "")
        ).lower()
        voice_map = {
            "stoic_male": "stoic",
            "power_male": "warrior",
            "warm_female": "cinematic",
            "hopeful_female": "calm",
        }
        selected = voice_map.get(voice_personality)
        if selected:
            scores[selected] += 3

    best = max(scores, key=scores.get) if scores else "cinematic"
    return best if scores.get(best, 0) > 0 else "cinematic"


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


def _extend_group_display_windows(groups, audio_duration):
    """Keep the spoken group visible through pauses without preloading future words."""
    if not groups:
        return groups

    normalized = []
    for index, group in enumerate(groups):
        item = dict(group)
        try:
            current_end = float(item.get("end", item.get("start", 0)))
        except (TypeError, ValueError):
            current_end = 0.0

        display_end = current_end
        if index + 1 < len(groups):
            try:
                next_start = float(groups[index + 1].get("start", current_end))
            except (TypeError, ValueError):
                next_start = current_end
            if next_start > display_end:
                display_end = next_start
        else:
            display_end = min(max(display_end, current_end), float(audio_duration))

        item["display_end"] = display_end
        normalized.append(item)

    return normalized


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
        return _extend_group_display_windows(plan, duration)

    aligned = caption_segments(audio_path, narration)
    if not aligned:
        return []

    return _extend_group_display_windows(
        _groups_from_aligned_words(aligned, plan=plan),
        duration,
    )


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
        "margin": (CAPTION_MARGIN, CAPTION_VERTICAL_MARGIN),
    }

    if font:
        kwargs["font"] = font

    return TextClip(**kwargs)


def _measure_words(words, font, font_size):
    """Measure caption words once at the requested font size."""
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


def _line_width(indices, measured):
    if not indices:
        return 0.0
    return sum(measured[i][0] for i in indices) + max(0, len(indices) - 1) * CAPTION_SPACING


def _line_break_penalty(words, split_index):
    """Penalize awkward phrase breaks while still allowing natural word wrapping."""
    left = str(words[split_index - 1]["word"]).lower().strip(".,!?;:")
    right = str(words[split_index]["word"]).lower().strip(".,!?;:")

    stopwords = {
        "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for",
        "with", "from", "at", "by", "as", "is", "are", "be", "your", "you",
    }

    penalty = 0.0
    if left in stopwords:
        penalty += 90.0
    if right in stopwords:
        penalty += 70.0

    raw_left = str(words[split_index - 1]["word"])
    if raw_left.endswith((',', ';', ':')):
        penalty -= 120.0
    elif raw_left.endswith(('.', '!', '?')):
        penalty -= 160.0

    return penalty


def _choose_balanced_lines(words, measured, max_width):
    """Return one line when it fits, otherwise the best two-line split."""
    count = len(words)
    all_indices = list(range(count))

    if _line_width(all_indices, measured) <= max_width:
        return [all_indices]

    if count <= 1:
        return None

    candidates = []
    for split in range(1, count):
        left = list(range(0, split))
        right = list(range(split, count))
        left_width = _line_width(left, measured)
        right_width = _line_width(right, measured)

        if left_width > max_width or right_width > max_width:
            continue

        total_width = max(left_width, right_width)
        balance = abs(left_width - right_width)
        count_balance = abs(len(left) - len(right)) * 35.0
        phrase_penalty = _line_break_penalty(words, split)

        score = balance + (total_width * 0.04) + count_balance + phrase_penalty
        candidates.append((score, left, right))

    if not candidates:
        return None

    candidates.sort(key=lambda item: item[0])
    _, left, right = candidates[0]
    return [left, right]


def _calculate_caption_layout(words, font, preferred=CAPTION_FONT_SIZE):
    """Choose a one/two-line layout, shrinking only when the safe width requires it."""
    size = int(preferred)
    min_size = int(CAPTION_MIN_FONT_SIZE)

    while size >= min_size:
        measured = _measure_words(words, font, size)
        lines = _choose_balanced_lines(words, measured, CAPTION_MAX_WIDTH)
        if lines:
            return size, measured, lines
        size -= 2

    # Exceptional fallback: keep the caption to at most two lines and make the
    # smallest practical reduction needed to fit an unusually long word.
    emergency_size = min_size
    while emergency_size >= 36:
        measured = _measure_words(words, font, emergency_size)
        lines = _choose_balanced_lines(words, measured, CAPTION_MAX_WIDTH)
        if lines:
            return emergency_size, measured, lines
        emergency_size -= 2

    measured = _measure_words(words, font, 36)
    # A single pathological word is still kept inside the safe area by using
    # the smallest emergency size only in this exceptional case.
    return 36, measured, [list(range(len(words)))]


def _keyword_category(word):
    token = _normalize_token(word)
    if not token:
        return None

    # A word can only receive one accent; the order below gives stronger,
    # more specific intent precedence over broader categories.
    priority = (
        "struggle",
        "discipline",
        "courage",
        "success",
        "hope",
        "vision",
        "growth",
        "time",
    )
    for category in priority:
        if token in PREMIUM_KEYWORDS[category]:
            return category
    return None


def _active_color(word, theme="cinematic"):
    style = str(word.get("style", "normal")).lower()
    supplied = str(word.get("color", "")).strip()

    if supplied and supplied.lower() not in {"#ffffff", "white"}:
        return supplied

    if style == "pain":
        return DEFAULT_PAIN
    if style == "hope":
        return DEFAULT_HOPE

    category = _keyword_category(word.get("word", ""))
    if category:
        # Keep the palette coherent with the video theme while preserving the
        # semantic accent family.
        color = PREMIUM_ACCENTS[category]
        if theme == "calm" and category in {"discipline", "courage"}:
            return "#67D6C8"
        if theme == "stoic" and category in {"success", "time", "vision"}:
            return "#E4C76B"
        if theme == "cinematic" and category == "struggle":
            return "#FF6B61"
        return color

    return DEFAULT_HIGHLIGHT


def _is_power_word(word):
    if str(word.get("animation", "")).lower() == "impact_pop":
        return True
    if str(word.get("style", "")).lower() in {"highlight", "pain", "hope"}:
        return True
    category = _keyword_category(word.get("word", ""))
    return category in {"success", "discipline", "courage", "struggle"}


def make_caption_group(group, font, theme="cinematic"):
    """Create a centered one/two-line caption group without changing word timing."""
    words = group.get("words", [])
    if not words:
        return []

    font_size, measured, lines = _calculate_caption_layout(words, font)

    line_widths = [_line_width(line, measured) for line in lines]
    line_heights = [max(measured[i][1] for i in line) for line in lines]
    total_height = sum(line_heights) + max(0, len(lines) - 1) * CAPTION_LINE_GAP

    safe_padding = CAPTION_STROKE + CAPTION_MARGIN
    safe_left = CAPTION_SAFE_LEFT + safe_padding
    safe_right = WIDTH - CAPTION_SAFE_RIGHT - safe_padding
    max_safe_width = max(1, safe_right - safe_left)

    # Keep the existing vertical safe-area/bottom-cropping fix intact while
    # adapting the total height for two-line captions.
    raw_top = CAPTION_CENTER_Y - total_height / 2
    min_top = CAPTION_SAFE_TOP + safe_padding
    max_top = CAPTION_SAFE_BOTTOM - total_height - safe_padding
    top = min(max(raw_top, min_top), max_top if max_top >= min_top else min_top)

    # Per-line centered positions. The accumulated y-offset keeps two-line
    # captions visually centered instead of pinning the second line low.
    line_positions = {}
    cursor_y = top
    for line, line_height, line_width in zip(lines, line_heights, line_widths):
        line_x = CAPTION_CENTER_X - line_width / 2
        line_x = min(max(line_x, safe_left), safe_right - line_width)
        for index in line:
            line_positions[index] = (
                line_x,
                cursor_y,
            )
            line_x += measured[index][0] + CAPTION_SPACING
        cursor_y += line_height + CAPTION_LINE_GAP

    clips = []

    group_start = float(group["start"])
    group_end = float(group["end"])
    # Keep already-spoken words visible through an audio pause, but never show
    # a future word before its own word-level timestamp.
    display_end = max(group_end, float(group.get("display_end", group_end)))

    # Do not let more than two keyword accents dominate a single caption group.
    accent_count = 0
    for index, word in enumerate(words):
        word_start = max(group_start, float(word["start"]))
        word_duration = max(0.01, display_end - word_start)
        x, y = line_positions[index]

        base = _make_word_clip(
            word["word"],
            font,
            font_size,
            DEFAULT_NORMAL,
        )
        base = (
            base.with_position((x, y))
            .with_start(word_start)
            .with_duration(word_duration)
        )
        clips.append(base)

    for index, word in enumerate(words):
        start = max(group_start, float(word["start"]))
        end = min(group_end, float(word["end"]))
        duration = end - start
        if duration <= 0:
            continue

        category = _keyword_category(word.get("word", ""))
        style = str(word.get("style", "normal")).lower()
        should_accent = bool(category) or style in {"highlight", "pain", "hope"}
        if should_accent and style == "normal":
            if accent_count >= 2:
                should_accent = False
            else:
                accent_count += 1

        if should_accent:
            color = _active_color(word, theme)
        else:
            # Preserve the existing active-word treatment for ordinary words,
            # but do not introduce another semantic accent after the small
            # per-group accent budget has been reached.
            color = DEFAULT_HIGHLIGHT
        active = _make_word_clip(
            word["word"],
            font,
            font_size,
            color,
        )
        active = (
            active.with_position(line_positions[index])
            .with_start(start)
            .with_duration(duration)
        )
        clips.append(active)

        if _is_power_word(word):
            pop_end = min(end, start + CAPTION_POP_DURATION)
            pop_duration = pop_end - start
            if pop_duration > 0:
                pop_size = min(font_size + 12, int(round(font_size * 1.14)))
                pop = _make_word_clip(
                    word["word"],
                    font,
                    pop_size,
                    _active_color(word, theme),
                )

                # Keep the pop inside both horizontal and vertical safe areas.
                while pop.w > max_safe_width and pop_size > 48:
                    safe_close(pop)
                    pop_size -= 2
                    pop = _make_word_clip(
                        word["word"],
                        font,
                        pop_size,
                        _active_color(word, theme),
                    )

                x, y = line_positions[index]
                center_x = x + measured[index][0] / 2
                center_y = y + measured[index][1] / 2
                pop_x = center_x - pop.w / 2
                pop_y = center_y - pop.h / 2

                pop_x = min(max(pop_x, safe_left), safe_right - pop.w)
                pop_min_y = CAPTION_SAFE_TOP + safe_padding
                pop_max_y = CAPTION_SAFE_BOTTOM - pop.h - safe_padding
                if pop_max_y >= pop_min_y:
                    pop_y = min(max(pop_y, pop_min_y), pop_max_y)
                else:
                    pop_y = pop_min_y

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
        "margin": (CAPTION_MARGIN, CAPTION_VERTICAL_MARGIN),
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
        brief = load_json(OUTPUT / "production_brief.json") if (OUTPUT / "production_brief.json").exists() else None
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
            clips.extend(make_caption_group(group, font, theme=theme))

        if clips:
            return clips

    # Final fallback for unusual runs where no aligned caption plan can be made.
    timings = caption_segments(audio, narration)

    if timings:
        fallback_groups = _extend_group_display_windows(
            _groups_from_aligned_words(timings, plan=None),
            get_audio_duration(),
        )
        brief = load_json(OUTPUT / "production_brief.json") if (OUTPUT / "production_brief.json").exists() else None
        theme = choose_caption_theme(narration, None, brief=brief)
        font = resolve_caption_font(theme)
        clips = []
        for group in fallback_groups:
            clips.extend(make_caption_group(group, font, theme=theme))
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
# INTELLIGENT VISUAL SELECTION
# =====================================================


def _token_set(text):
    return {
        token
        for token in re.findall(r"[a-z0-9']+", str(text or "").lower())
        if len(token) > 2
    }


VISUAL_SEMANTIC_GROUPS = {
    "ashes": {"ash", "ashes", "burn", "burnt", "ember", "embers", "smoke", "charred", "fire", "forest"},
    "phoenix": {"phoenix", "rebirth", "rise", "rising", "flame", "fire", "ember", "embers", "ashes"},
    "solitude": {"alone", "solitude", "lonely", "silhouette", "desolate", "mist", "fog", "isolation", "night"},
    "doubt": {"doubt", "doubts", "reflection", "mirror", "contemplation", "uncertain", "uncertainty", "thoughtful"},
    "hope": {"hope", "light", "golden", "sunrise", "glow", "bright", "uplifting"},
    "strength": {"strength", "warrior", "battle", "training", "power", "strong", "resilience", "sacrifice"},
    "wisdom": {"ancient", "roman", "marble", "statue", "manuscript", "philosophy", "stoic", "library", "temple"},
}


def _expanded_semantics(tokens):
    groups = set()
    for group, members in VISUAL_SEMANTIC_GROUPS.items():
        if tokens & members:
            groups.add(group)
    return groups


def _scene_text(scene):
    visual = scene.get("visual", {}) or {}
    return " ".join(
        [
            str(scene.get("voice_line", "")),
            str(scene.get("caption", "")),
            str(scene.get("pexels_query", "")),
            str(visual.get("type", "")),
            str(visual.get("subject", "")),
            str(visual.get("action", "")),
            str(visual.get("emotion", "")),
            str(visual.get("environment", "")),
            str(visual.get("composition", "")),
        ]
    )


def _asset_text(asset):
    return " ".join(
        [
            str(asset.get("alt", "")),
            str(asset.get("url", "")),
            str(asset.get("preview", "")),
        ]
    )


def _asset_score(asset, scene, asset_type, used_counts):
    scene_tokens = _token_set(_scene_text(scene))
    asset_tokens = _token_set(_asset_text(asset))
    query_tokens = _token_set(scene.get("pexels_query", ""))

    overlap = len(scene_tokens & asset_tokens) / max(len(scene_tokens), 1)
    query_overlap = len(query_tokens & asset_tokens) / max(len(query_tokens), 1)

    scene_groups = _expanded_semantics(scene_tokens | query_tokens)
    asset_groups = _expanded_semantics(asset_tokens)
    semantic_overlap = len(scene_groups & asset_groups) / max(len(scene_groups), 1)

    visual = scene.get("visual", {}) or {}
    descriptors = " ".join(
        [
            str(visual.get("type", "")),
            str(visual.get("action", "")),
            str(visual.get("subject", "")),
            str(visual.get("composition", "")),
        ]
    ).lower()

    motion_words = {
        "walking", "running", "rising", "falling", "training",
        "fighting", "climbing", "moving", "opening", "turning",
        "storm", "waves", "wind", "journey", "action", "slow-motion",
    }
    still_words = {
        "object", "statue", "manuscript", "book", "key", "hourglass",
        "portrait", "close-up", "symbol", "marble", "painting",
        "reflection", "still", "architecture", "candle", "phoenix",
        "ashes", "ash", "embers", "flame",
    }

    type_bias = 0.0
    if asset_type == "video" and any(word in descriptors for word in motion_words):
        type_bias += 0.16
    if asset_type == "image" and any(word in descriptors for word in still_words):
        type_bias += 0.18

    visual_type = str(visual.get("type", "")).lower()
    if asset_type == "image" and visual_type in {"close-up", "detail shot", "environmental shot", "symbolic", "still"}:
        type_bias += 0.10
    if asset_type == "video" and visual_type in {"action", "slow-motion", "tracking shot", "movement"}:
        type_bias += 0.10

    # Images are deliberately allowed to win symbolic/abstract beats so the
    # renderer does not turn every sentence into moving stock footage.
    symbolic_groups = {"ashes", "phoenix", "doubt", "hope", "wisdom"}
    if asset_type == "image" and scene_groups & symbolic_groups:
        type_bias += 0.18

    used = int(used_counts.get(str(asset.get("id")), 0))
    reuse_penalty = 0.14 * used

    duration_bonus = 0.0
    if asset_type == "video":
        duration = _safe_float(asset.get("duration", 0))
        duration_bonus = min(0.06, max(0.0, duration - 5.0) / 45.0)

    return (
        overlap * 0.38
        + query_overlap * 0.16
        + semantic_overlap * 0.26
        + type_bias
        + duration_bonus
        - reuse_penalty
    )


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


SHORT_FORMAT_HISTORY_GROUPS = {
    "historical",
    "warrior",
    "ancient",
    "stoic",
    "classical",
    "statue",
    "sculpture",
    "roman",
    "greek",
    "civilization",
    "leader",
    "leaders",
    "philosopher",
}

SHORT_FORMAT_MOTION_WORDS = {
    "action", "active", "battle", "battling", "climb", "climbing",
    "drive", "driving", "fight", "fighting", "journey", "moving",
    "movement", "run", "running", "storm", "training", "travel",
    "walking", "waves", "wind", "motion", "slow-motion", "tracking",
    "chase", "escape", "breakthrough", "workout", "sprinting",
}

SHORT_FORMAT_STILL_WORDS = {
    "ancient", "aurelius", "marble", "manuscript", "portrait",
    "sculpture", "statue", "painting", "classical", "roman", "greek",
    "philosopher", "historical", "leader", "leaders", "wisdom",
    "stoic", "stoicism", "civilization", "symbolic", "symbolism",
    "still", "monument", "bust", "relief",
}


def _full_short_text(brief):
    """Build one deterministic text representation for whole-Short format choice."""
    if not isinstance(brief, dict):
        return ""

    parts = [
        str(brief.get("title", "")),
        str(brief.get("theme", "")),
        str(brief.get("narration", "")),
        str(brief.get("hook", "")),
    ]

    creative = brief.get("creative_direction", {}) or {}
    voice = brief.get("voice_direction", {}) or {}
    parts.extend(
        str(creative.get(key, ""))
        for key in ("philosophical_theme", "visual_style", "emotional_arc", "color_mood", "ending_style")
    )
    parts.extend(
        str(voice.get(key, ""))
        for key in ("emotion", "intensity", "pace", "personality")
    )

    for scene in brief.get("scenes", []) or []:
        parts.append(_scene_text(scene))

    return " ".join(parts).lower()


def _determine_short_asset_type(brief, assets):
    """Choose ONE visual format for the entire Short. Never mix formats."""
    text = _full_short_text(brief)
    tokens = _token_set(text)

    # Historical / classical strength figures are explicitly image-first.
    historical_hits = len(tokens & SHORT_FORMAT_HISTORY_GROUPS)
    if historical_hits >= 2 or any(phrase in text for phrase in (
        "marcus aurelius",
        "powerful historical figure",
        "historical strength figure",
        "legendary warrior",
        "ancient warrior",
        "classical statue",
        "roman emperor",
        "ancient civilization",
    )):
        return "image"

    motion_score = len(tokens & SHORT_FORMAT_MOTION_WORDS)
    still_score = len(tokens & SHORT_FORMAT_STILL_WORDS)

    creative = brief.get("creative_direction", {}) if isinstance(brief, dict) else {}
    visual_style = str(creative.get("visual_style", "")).lower()
    philosophical_theme = str(creative.get("philosophical_theme", "")).lower()

    if "symbolic" in visual_style or "portrait" in visual_style:
        still_score += 2
    if "cinematic" in visual_style or "dynamic" in visual_style or "action" in visual_style:
        motion_score += 2
    if any(term in philosophical_theme for term in ("stoic", "ancient", "classical", "wisdom")):
        still_score += 2

    # Strong action/movement concepts should genuinely use footage when available.
    if motion_score >= still_score + 2:
        preferred = "video"
    elif still_score >= motion_score + 2:
        preferred = "image"
    else:
        # Default toward video when both formats are plausible so the factory
        # does not drift into image-only output.
        preferred = "video"

    available = {
        "video": any(group.get("videos") for group in assets.get("videos", [])),
        "image": any(group.get("images") for group in assets.get("images", [])),
    }

    if available.get(preferred):
        return preferred
    if available.get("video"):
        return "video"
    if available.get("image"):
        return "image"
    return preferred


def _choose_scene_asset(scene, video_group, image_group, used_counts, previous, selected_asset_type):
    """Choose the best asset, restricted to the Short-wide selected format."""
    if selected_asset_type == "video":
        candidates = [
            (asset, "video")
            for asset in (video_group or [])
            if asset.get("video_file")
        ]
    else:
        candidates = [
            (asset, "image")
            for asset in (image_group or [])
            if asset.get("image")
        ]

    if not candidates:
        return None, "none", False

    scored = [
        (_asset_score(asset, scene, selected_asset_type, used_counts), asset, selected_asset_type)
        for asset, _ in candidates
    ]
    scored.sort(key=lambda item: item[0], reverse=True)

    # Prefer a fresh asset whenever one is close to the best result.
    fresh = [
        item
        for item in scored
        if int(used_counts.get(str(item[1].get("id")), 0)) == 0
    ]
    if fresh:
        top_score = scored[0][0]
        near_best_fresh = [item for item in fresh if item[0] >= top_score - 0.10]
        if near_best_fresh:
            _, asset, _ = near_best_fresh[0]
        else:
            _, asset, _ = fresh[0]
        return asset, selected_asset_type, False

    # Controlled reuse stays inside the selected whole-Short format.
    scene_tokens = _token_set(_scene_text(scene))
    for _, prior_scene, prior_asset in previous:
        if not prior_asset:
            continue
        if selected_asset_type == "video" and not prior_asset.get("video_file"):
            continue
        if selected_asset_type == "image" and not prior_asset.get("image"):
            continue

        overlap = len(scene_tokens & _token_set(_scene_text(prior_scene))) / max(len(scene_tokens), 1)
        if overlap >= 0.35 and int(used_counts.get(str(prior_asset.get("id")), 0)) < 2:
            for score, asset, _ in scored:
                if str(asset.get("id")) == str(prior_asset.get("id")):
                    return asset, selected_asset_type, True

    _, asset, _ = scored[0]
    return asset, selected_asset_type, True


def _scene_crop_treatment(scene, index, reused=False):
    visual = scene.get("visual", {}) or {}
    composition = str(visual.get("composition", "")).lower()
    focus_x = 0.5
    if "left" in composition:
        focus_x = 0.42
    elif "right" in composition:
        focus_x = 0.58

    # Deterministic micro-variation prevents repeated assets from becoming
    # visually identical while preserving the original scene composition.
    if reused:
        focus_x += 0.06 if index % 2 == 0 else -0.06

    focus_x = min(0.62, max(0.38, focus_x))
    zoom = 1.03 + (0.02 * (index % 3))
    if reused:
        zoom += 0.02
    return focus_x, zoom


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
        video_groups = {
            int(group.get("scene")): group.get("videos", [])
            for group in assets.get("videos", [])
            if str(group.get("scene", "")).isdigit()
        }
        image_groups = {
            int(group.get("scene")): group.get("images", [])
            for group in assets.get("images", [])
            if str(group.get("scene", "")).isdigit()
        }

        selected_asset_type = _determine_short_asset_type(brief, assets)
        print(f"Whole-Short visual format: {selected_asset_type.upper()} assets only")

        used_counts = {}
        previous_selections = []

        for scene_index, scene in enumerate(brief.get("scenes", []), start=1):
            scene_id = int(scene.get("scene", scene_index))
            asset, asset_type, reused = _choose_scene_asset(
                scene,
                video_groups.get(scene_id, []),
                image_groups.get(scene_id, []),
                used_counts,
                previous_selections,
                selected_asset_type,
            )

            focus_x, zoom = _scene_crop_treatment(
                scene,
                scene_index,
                reused=reused,
            )

            if asset:
                used_counts[str(asset.get("id"))] = int(
                    used_counts.get(str(asset.get("id")), 0)
                ) + 1

            previous_selections.append((scene, scene, asset))

            print(
                f"Scene {scene_id}: visual asset -> {asset_type}"
                f"{' (controlled reuse)' if reused else ''}"
                f" id={asset.get('id') if asset else 'none'}"
            )

            clips.append(
                create_visual(
                    asset,
                    duration,
                    focus_x=focus_x,
                    zoom=zoom,
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

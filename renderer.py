"""
Motivational Factory V6 Production Renderer

Purpose:
    Connect the existing production artifacts into a finished
    vertical motivational Short.

Inputs:
    output/production_brief.json
    output/visual_assets.json
    output/caption_plan.json
    output/voice.wav
    output/music.mp3 (optional)
    output/sfx.wav (optional)

Output:
    output/final_short.mp4
"""

import json
import os
import re
from pathlib import Path

import requests
import numpy as np

from moviepy import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ColorClip,
    vfx,
    afx,
)

from PIL import (
    Image,
    ImageDraw,
    ImageFont,
    ImageFilter,
)


# =====================================================
# PATHS / FORMAT
# =====================================================

OUTPUT = Path(
    os.getenv(
        "MOTIVATIONAL_OUTPUT_DIR",
        "output"
    )
)
OUTPUT.mkdir(
    parents=True,
    exist_ok=True
)

FINAL_VIDEO = OUTPUT / "final_short.mp4"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

TRANSITION_SECONDS = 0.35
MIN_SCENE_SECONDS = 1.0


# =====================================================
# CINEMATIC RULE ENGINE
# =====================================================

FORBIDDEN = [
    "selfie",
    "influencer",
    "phone",
    "laptop",
    "office worker",
    "generic businessman",
    "social media",
    "meeting",
]


SYMBOLIC_KEYWORDS = {
    "discipline": [
        "mountain",
        "storm",
        "stone",
        "armor",
        "ancient",
    ],
    "wisdom": [
        "library",
        "statue",
        "manuscript",
        "ruins",
        "temple",
    ],
    "success": [
        "sunrise",
        "architecture",
        "city",
        "golden",
    ],
    "failure": [
        "dark",
        "rain",
        "broken",
        "storm",
    ],
    "growth": [
        "forest",
        "path",
        "light",
        "nature",
    ],
}


# =====================================================
# HELPERS
# =====================================================

def load_json(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


def download(url, filename):

    if not url:

        raise ValueError(
            "Empty media URL"
        )

    target = OUTPUT / filename

    if (
        target.exists()
        and target.stat().st_size > 0
    ):

        return target

    response = requests.get(
        url,
        timeout=120,
        stream=True
    )

    response.raise_for_status()

    with open(
        target,
        "wb"
    ) as f:

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):

            if chunk:

                f.write(chunk)

    if (
        not target.exists()
        or target.stat().st_size == 0
    ):

        raise RuntimeError(
            f"Downloaded media is empty: {url}"
        )

    return target


def safe_float(
    value,
    default=0.0
):

    try:

        return float(
            value
        )

    except (
        TypeError,
        ValueError
    ):

        return float(
            default
        )


def word_tokens(text):

    return re.findall(
        r"[A-Za-z0-9']+",
        str(text).lower()
    )


def scene_text(scene):

    visual = scene.get(
        "visual",
        {}
    )

    return " ".join(
        [
            str(
                scene.get(
                    "voice_line",
                    ""
                )
            ),
            str(
                scene.get(
                    "pexels_query",
                    ""
                )
            ),
            str(
                visual.get(
                    "type",
                    ""
                )
            ),
            str(
                visual.get(
                    "subject",
                    ""
                )
            ),
            str(
                visual.get(
                    "action",
                    ""
                )
            ),
            str(
                visual.get(
                    "emotion",
                    ""
                )
            ),
            str(
                visual.get(
                    "environment",
                    ""
                )
            ),
            str(
                visual.get(
                    "camera",
                    ""
                )
            ),
            str(
                visual.get(
                    "composition",
                    ""
                )
            ),
            str(
                visual.get(
                    "lighting",
                    ""
                )
            ),
        ]
    )


# =====================================================
# ASSET NORMALIZATION
# =====================================================

def normalize_asset_groups(
    raw_assets
):

    """
    Supports both the original list structure and the
    current factory structure:

        {
            "videos": [...scene groups...],
            "images": [...scene groups...]
        }
    """

    if isinstance(
        raw_assets,
        list
    ):

        return raw_assets

    if not isinstance(
        raw_assets,
        dict
    ):

        return []

    groups = {}

    for entry in raw_assets.get(
        "videos",
        []
    ) or []:

        if not isinstance(
            entry,
            dict
        ):

            continue

        scene_number = entry.get(
            "scene"
        )

        group = groups.setdefault(
            scene_number,
            {
                "scene":
                    scene_number,
                "visual":
                    entry.get(
                        "visual",
                        {}
                    ),
                "pexels_query":
                    entry.get(
                        "pexels_query",
                        ""
                    ),
                "videos": [],
                "images": [],
            }
        )

        if not group.get(
            "visual"
        ):

            group[
                "visual"
            ] = entry.get(
                "visual",
                {}
            )

        if not group.get(
            "pexels_query"
        ):

            group[
                "pexels_query"
            ] = entry.get(
                "pexels_query",
                ""
            )

        group[
            "videos"
        ].extend(
            entry.get(
                "videos",
                []
            ) or []
        )

    for entry in raw_assets.get(
        "images",
        []
    ) or []:

        if not isinstance(
            entry,
            dict
        ):

            continue

        scene_number = entry.get(
            "scene"
        )

        group = groups.setdefault(
            scene_number,
            {
                "scene":
                    scene_number,
                "visual":
                    entry.get(
                        "visual",
                        {}
                    ),
                "pexels_query":
                    entry.get(
                        "pexels_query",
                        ""
                    ),
                "videos": [],
                "images": [],
            }
        )

        if not group.get(
            "visual"
        ):

            group[
                "visual"
            ] = entry.get(
                "visual",
                {}
            )

        if not group.get(
            "pexels_query"
        ):

            group[
                "pexels_query"
            ] = entry.get(
                "pexels_query",
                ""
            )

        group[
            "images"
        ].extend(
            entry.get(
                "images",
                []
            ) or []
        )

    return list(
        groups.values()
    )


def group_for_scene(
    scene_number,
    groups
):

    for group in groups:

        if group.get(
            "scene"
        ) == scene_number:

            return group

    return {}


# =====================================================
# ASSET URL RESOLUTION
# =====================================================

def asset_is_image(asset):

    if asset.get(
        "type"
    ) == "image":

        return True

    if asset.get(
        "image"
    ):

        return True

    return False


def asset_url(asset):

    if asset_is_image(
        asset
    ):

        return (
            asset.get(
                "image"
            )
            or asset.get(
                "preview"
            )
            or asset.get(
                "url"
            )
        )

    return (
        asset.get(
            "video_file"
        )
        or asset.get(
            "url"
        )
    )


# =====================================================
# ASSET INTELLIGENCE
# =====================================================

def score_asset(
    asset,
    scene
):

    score = 0.0

    asset_text = json.dumps(
        asset,
        ensure_ascii=False
    ).lower()

    scene_text_value = scene_text(
        scene
    ).lower()

    for forbidden in FORBIDDEN:

        if forbidden in asset_text:

            score -= 100.0

    scene_tokens = set(
        word_tokens(
            scene_text_value
        )
    )

    asset_tokens = set(
        word_tokens(
            asset_text
        )
    )

    overlap = len(
        scene_tokens.intersection(
            asset_tokens
        )
    )

    score += min(
        25.0,
        overlap * 2.5
    )

    for category, words in SYMBOLIC_KEYWORDS.items():

        if category in scene_text_value:

            for word in words:

                if word in asset_text:

                    score += 10.0

    duration = safe_float(
        asset.get(
            "duration"
        )
    )

    width = safe_float(
        asset.get(
            "width"
        )
    )

    height = safe_float(
        asset.get(
            "height"
        )
    )

    if duration >= 5:

        score += 5.0

    if duration >= 8:

        score += 3.0

    if width > 0 and height > 0:

        if width >= height:

            score += 8.0

        pixels = width * height

        if pixels >= 3840 * 2160:

            score += 12.0

        elif pixels >= 2560 * 1440:

            score += 9.0

        elif pixels >= 1920 * 1080:

            score += 6.0

    quality = str(
        asset.get(
            "quality",
            ""
        )
    ).lower()

    if quality == "uhd":

        score += 5.0

    elif quality == "hd":

        score += 3.0

    if asset_is_image(
        asset
    ):

        score += 1.0

    else:

        score += 4.0

    return score


def choose_best_asset(
    scene,
    group
):

    candidates = []

    for item in group.get(
        "videos",
        []
    ) or []:

        if isinstance(
            item,
            dict
        ):

            candidate = dict(
                item
            )

            candidate[
                "type"
            ] = "video"

            candidates.append(
                candidate
            )

    for item in group.get(
        "images",
        []
    ) or []:

        if isinstance(
            item,
            dict
        ):

            candidate = dict(
                item
            )

            candidate[
                "type"
            ] = "image"

            candidates.append(
                candidate
            )

    candidates = [
        item
        for item in candidates
        if asset_url(
            item
        )
    ]

    if not candidates:

        return None

    return max(
        candidates,
        key=lambda item: score_asset(
            item,
            scene
        )
    )


# =====================================================
# MEDIA FRAMING
# =====================================================

def crop_vertical(
    clip
):

    scale = max(
        WIDTH / clip.w,
        HEIGHT / clip.h
    )

    clip = clip.resized(
        scale
    )

    return clip.cropped(
        x_center=clip.w / 2,
        y_center=clip.h / 2,
        width=WIDTH,
        height=HEIGHT
    )


def fit_video_duration(
    clip,
    duration
):

    duration = max(
        MIN_SCENE_SECONDS,
        float(duration)
    )

    if clip.duration < duration:

        clip = clip.with_effects(
            [
                vfx.Loop(
                    duration=duration
                )
            ]
        )

    else:

        clip = clip.subclipped(
            0,
            min(
                clip.duration,
                duration
            )
        )

    clip = crop_vertical(
        clip
    )

    return clip.with_duration(
        duration
    )


def fit_image_duration(
    clip,
    duration
):

    duration = max(
        MIN_SCENE_SECONDS,
        float(duration)
    )

    clip = crop_vertical(
        clip
    )

    base_width = clip.w
    base_height = clip.h
    scale_duration = max(
        0.001,
        duration
    )

    def zoom(t):

        return (
            1.0
            + 0.04
            * (
                min(
                    max(
                        float(t),
                        0.0
                    ),
                    scale_duration
                )
                / scale_duration
            )
        )

    # Keep movement subtle and cinematic.
    return clip.with_duration(
        duration
    ).resized(
        zoom
    ).cropped(
        x_center=base_width / 2,
        y_center=base_height / 2,
        width=WIDTH,
        height=HEIGHT
    )


# =====================================================
# SCENE TIMING
# =====================================================

def scene_timings_from_captions(
    scenes,
    caption_plan,
    audio_duration
):

    if not scenes:

        return []

    if not caption_plan:

        word_counts = [
            max(
                1,
                len(
                    str(
                        scene.get(
                            "voice_line",
                            ""
                        )
                    ).split()
                )
            )
            for scene in scenes
        ]

        total_words = max(
            1,
            sum(word_counts)
        )

        timings = []
        cursor = 0.0

        for index, count in enumerate(
            word_counts
        ):

            if index == len(
                word_counts
            ) - 1:

                end = audio_duration

            else:

                end = (
                    cursor
                    + audio_duration
                    * count
                    / total_words
                )

            timings.append(
                {
                    "start": cursor,
                    "end": max(
                        cursor + MIN_SCENE_SECONDS,
                        end
                    ),
                }
            )

            cursor = timings[-1][
                "end"
            ]

        timings[-1][
            "end"
        ] = audio_duration

        return timings

    caption_end = safe_float(
        caption_plan[-1].get(
            "end",
            0
        )
    )

    scale = (
        audio_duration / caption_end
        if caption_end > 0
        else 1.0
    )

    caption_words = []

    for caption in caption_plan:

        words = caption.get(
            "words",
            []
        )

        if isinstance(
            words,
            list
        ) and words:

            count = len(
                words
            )

        else:

            count = len(
                str(
                    caption.get(
                        "text",
                        ""
                    )
                ).split()
            )

        caption_words.append(
            max(
                1,
                count
            )
        )

    scene_word_counts = [
        max(
            1,
            len(
                str(
                    scene.get(
                        "voice_line",
                        ""
                    )
                ).split()
            )
        )
        for scene in scenes
    ]

    timings = []

    caption_index = 0
    cursor = 0.0

    for scene_index, target_words in enumerate(
        scene_word_counts
    ):

        consumed = 0

        start = cursor
        end = start

        while (
            caption_index < len(
                caption_plan
            )
            and (
                consumed < target_words
                or end <= start
            )
        ):

            item = caption_plan[
                caption_index
            ]

            end = safe_float(
                item.get(
                    "end",
                    item.get(
                        "start",
                        0
                    )
                )
            ) * scale

            consumed += caption_words[
                caption_index
            ]

            caption_index += 1

        if scene_index == len(
            scene_word_counts
        ) - 1:

            end = audio_duration

        end = min(
            audio_duration,
            max(
                start + MIN_SCENE_SECONDS,
                end
            )
        )

        timings.append(
            {
                "start": start,
                "end": end,
            }
        )

        cursor = end

    timings[-1][
        "end"
    ] = audio_duration

    return timings


# =====================================================
# SCENE CREATION
# =====================================================

def create_scene(
    scene,
    asset,
    duration
):

    duration = max(
        MIN_SCENE_SECONDS,
        float(duration)
    )

    if not asset:

        return ColorClip(
            size=(
                WIDTH,
                HEIGHT
            ),
            color=(
                0,
                0,
                0
            )
        ).with_duration(
            duration
        )

    url = asset_url(
        asset
    )

    if not url:

        return ColorClip(
            size=(
                WIDTH,
                HEIGHT
            ),
            color=(
                0,
                0,
                0
            )
        ).with_duration(
            duration
        )

    extension = (
        ".jpg"
        if asset_is_image(
            asset
        )
        else ".mp4"
    )

    filename = (
        f"scene_{scene.get('scene')}{extension}"
    )

    path = download(
        url,
        filename
    )

    if asset_is_image(
        asset
    ):

        clip = ImageClip(
            str(path)
        )

        clip = fit_image_duration(
            clip,
            duration
        )

    else:

        clip = VideoFileClip(
            str(path),
            audio=False
        )

        clip = fit_video_duration(
            clip,
            duration
        )

    fade = min(
        0.45,
        duration / 3
    )

    return clip.with_effects(
        [
            vfx.FadeIn(
                fade
            ),
            vfx.FadeOut(
                fade
            ),
        ]
    ).with_duration(
        duration
    )


# =====================================================
# CAPTION RENDERING
# =====================================================

def find_font():

    candidates = [
        "/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf",
        "/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.otf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]

    for path in candidates:

        if Path(path).exists():

            return path

    return None


CAPTION_FONT_PATH = find_font()


def load_font(size):

    if CAPTION_FONT_PATH:

        return ImageFont.truetype(
            CAPTION_FONT_PATH,
            size
        )

    return ImageFont.load_default()


def hex_to_rgb(
    value
):

    value = str(
        value or "#FFFFFF"
    )

    if not value.startswith(
        "#"
    ):

        value = "#" + value

    try:

        return tuple(
            int(
                value[index:index + 2],
                16
            )
            for index in (
                1,
                3,
                5
            )
        )

    except Exception:

        return (
            255,
            255,
            255
        )


def caption_image(
    caption
):

    text = str(
        caption.get(
            "text",
            ""
        )
    ).strip()

    if not text:

        return None

    words = caption.get(
        "words",
        []
    )

    if not isinstance(
        words,
        list
    ) or not words:

        words = [
            {
                "word":
                    word,
                "style":
                    "normal",
                "color":
                    "#FFFFFF",
            }
            for word in text.split()
        ]

    font = load_font(
        72
    )

    max_width = 920
    spacing = 18
    line_height = 96
    padding_x = 40
    padding_y = 35

    def width_of(
        word
    ):

        box = font.getbbox(
            word
        )

        return box[2] - box[0]

    lines = []
    current = []
    current_width = 0

    for item in words:

        word = str(
            item.get(
                "word",
                ""
            )
        ).strip()

        if not word:

            continue

        word_width = width_of(
            word
        )

        projected = (
            word_width
            if not current
            else (
                current_width
                + spacing
                + word_width
            )
        )

        if (
            current
            and projected > max_width
        ):

            lines.append(
                current
            )

            current = [
                item
            ]

            current_width = word_width

        else:

            current.append(
                item
            )

            current_width = projected

    if current:

        lines.append(
            current
        )

    if not lines:

        return None

    width = (
        max_width
        + padding_x * 2
    )

    height = (
        len(lines)
        * line_height
        + padding_y * 2
    )

    image = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    glow = Image.new(
        "RGBA",
        (
            width,
            height
        ),
        (
            0,
            0,
            0,
            0
        )
    )

    draw = ImageDraw.Draw(
        image
    )

    glow_draw = ImageDraw.Draw(
        glow
    )

    y = padding_y

    for line in lines:

        line_width = 0

        for index, item in enumerate(
            line
        ):

            line_width += width_of(
                str(
                    item.get(
                        "word",
                        ""
                    )
                ).strip()
            )

            if index:

                line_width += spacing

        x = (
            width
            - line_width
        ) / 2

        for item in line:

            word = str(
                item.get(
                    "word",
                    ""
                )
            ).strip()

            if not word:

                continue

            fill = hex_to_rgb(
                item.get(
                    "color",
                    "#FFFFFF"
                )
            )

            glow_draw.text(
                (
                    x,
                    y
                ),
                word,
                font=font,
                fill=(
                    fill[0],
                    fill[1],
                    fill[2],
                    190
                ),
                stroke_width=8,
                stroke_fill=(
                    fill[0],
                    fill[1],
                    fill[2],
                    120
                )
            )

            draw.text(
                (
                    x + 2,
                    y + 4
                ),
                word,
                font=font,
                fill=(
                    0,
                    0,
                    0,
                    185
                ),
                stroke_width=8,
                stroke_fill=(
                    0,
                    0,
                    0,
                    220
                )
            )

            draw.text(
                (
                    x,
                    y
                ),
                word,
                font=font,
                fill=fill,
                stroke_width=3,
                stroke_fill=(
                    0,
                    0,
                    0,
                    230
                )
            )

            x += (
                width_of(
                    word
                )
                + spacing
            )

        y += line_height

    glow = glow.filter(
        ImageFilter.GaussianBlur(
            18
        )
    )

    image = Image.alpha_composite(
        glow,
        image
    )

    return np.array(
        image
    )


def caption_position(
    caption,
    image_width,
    image_height
):

    position = str(
        caption.get(
            "position",
            "center"
        )
    ).lower()

    x = (
        WIDTH
        - image_width
    ) / 2

    if position == "top":

        y = HEIGHT * 0.12

    elif position == "bottom":

        y = HEIGHT * 0.74

    else:

        y = (
            HEIGHT
            - image_height
        ) / 2

    return (
        x,
        y
    )


def build_caption_clips(
    caption_plan,
    audio_duration
):

    clips = []

    if not caption_plan:

        return clips

    plan_end = safe_float(
        caption_plan[-1].get(
            "end",
            0
        )
    )

    scale = (
        audio_duration / plan_end
        if plan_end > 0
        else 1.0
    )

    for caption in caption_plan:

        image_array = caption_image(
            caption
        )

        if image_array is None:

            continue

        start = (
            safe_float(
                caption.get(
                    "start",
                    0
                )
            )
            * scale
        )

        end = min(
            audio_duration,
            safe_float(
                caption.get(
                    "end",
                    start
                )
            ) * scale
        )

        duration = end - start

        if duration <= 0:

            continue

        overlay = ImageClip(
            image_array
        ).with_duration(
            duration
        )

        overlay = overlay.with_position(
            caption_position(
                caption,
                overlay.w,
                overlay.h
            )
        ).with_start(
            start
        )

        clips.append(
            overlay
        )

    return clips


# =====================================================
# AUDIO
# =====================================================

def get_voice_duration():

    path = OUTPUT / "voice.wav"

    if not path.exists():

        raise FileNotFoundError(
            f"Missing voice.wav: {path}"
        )

    audio = AudioFileClip(
        str(path)
    )

    duration = float(
        audio.duration
    )

    audio.close()

    return duration


def build_audio_mix(
    duration
):

    tracks = []

    voice_path = OUTPUT / "voice.wav"

    if voice_path.exists():

        voice = AudioFileClip(
            str(voice_path)
        )

        voice = voice.subclipped(
            0,
            min(
                voice.duration,
                duration
            )
        )

        tracks.append(
            voice
        )

    music_path = OUTPUT / "music.mp3"

    if music_path.exists():

        music = AudioFileClip(
            str(music_path)
        )

        if music.duration < duration:

            loops = int(
                duration / music.duration
            ) + 1

            pieces = [
                music
                for _ in range(
                    loops
                )
            ]

            music = concatenate_videoclips(
                []
            ) if False else music

            # MoviePy's audio_loop effect is stable in MoviePy 2.
            music = music.with_effects(
                [
                    afx.AudioLoop(
                        duration=duration
                    )
                ]
            )

        else:

            music = music.subclipped(
                0,
                duration
            )

        music = music.with_volume_scaled(
            0.18
        )

        tracks.append(
            music
        )

    sfx_path = OUTPUT / "sfx.wav"

    if sfx_path.exists():

        sfx = AudioFileClip(
            str(sfx_path)
        )

        if sfx.duration > duration:

            sfx = sfx.subclipped(
                0,
                duration
            )

        sfx = sfx.with_volume_scaled(
            0.25
        )

        tracks.append(
            sfx
        )

    if not tracks:

        return None

    return CompositeAudioClip(
        tracks
    ).with_duration(
        duration
    )


# =====================================================
# MAIN RENDER
# =====================================================

def render():

    print(
        "V6 Premium Renderer Starting"
    )

    brief_path = (
        OUTPUT
        / "production_brief.json"
    )

    assets_path = (
        OUTPUT
        / "visual_assets.json"
    )

    captions_path = (
        OUTPUT
        / "caption_plan.json"
    )

    if not brief_path.exists():

        raise FileNotFoundError(
            f"Missing production_brief.json: {brief_path}"
        )

    if not assets_path.exists():

        raise FileNotFoundError(
            f"Missing visual_assets.json: {assets_path}"
        )

    brief = load_json(
        brief_path
    )

    raw_assets = load_json(
        assets_path
    )

    caption_plan = []

    if captions_path.exists():

        caption_plan = load_json(
            captions_path
        )

    groups = normalize_asset_groups(
        raw_assets
    )

    scene_data = brief.get(
        "scenes",
        []
    )

    if not scene_data:

        raise RuntimeError(
            "No scenes found in production_brief.json."
        )

    audio_duration = get_voice_duration()

    timings = scene_timings_from_captions(
        scene_data,
        caption_plan,
        audio_duration
    )

    scene_clips = []

    for index, scene in enumerate(
        scene_data
    ):

        group = group_for_scene(
            scene.get(
                "scene"
            ),
            groups
        )

        selected = choose_best_asset(
            scene,
            group
        )

        timing = timings[
            min(
                index,
                len(
                    timings
                ) - 1
            )
        ]

        scene_duration = (
            timing["end"]
            - timing["start"]
        )

        print(
            "Scene",
            scene.get(
                "scene"
            ),
            "duration:",
            round(
                scene_duration,
                2
            ),
            "asset:",
            selected
        )

        scene_clips.append(
            create_scene(
                scene,
                selected,
                scene_duration
            )
        )

    if len(
        scene_clips
    ) == 1:

        final = scene_clips[0]

    else:

        final = scene_clips[0]

        cursor = scene_clips[0].duration

        for clip in scene_clips[1:]:

            overlap = min(
                TRANSITION_SECONDS,
                max(
                    0.0,
                    min(
                        final.duration,
                        clip.duration
                    ) / 3
                )
            )

            clip = clip.with_effects(
                [
                    vfx.CrossFadeIn(
                        overlap
                    )
                ]
            ).with_start(
                max(
                    0.0,
                    cursor - overlap
                )
            )

            final = CompositeVideoClip(
                [
                    final,
                    clip
                ],
                size=(
                    WIDTH,
                    HEIGHT
                )
            )

            cursor += (
                clip.duration
                - overlap
            )

        final = final.with_duration(
            audio_duration
        )

    audio = build_audio_mix(
        audio_duration
    )

    if audio is not None:

        final = final.with_audio(
            audio
        )

    caption_clips = build_caption_clips(
        caption_plan,
        audio_duration
    )

    if caption_clips:

        final = CompositeVideoClip(
            [
                final,
                *caption_clips,
            ],
            size=(
                WIDTH,
                HEIGHT
            )
        ).with_duration(
            audio_duration
        )

    final.write_videofile(
        str(
            FINAL_VIDEO
        ),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=os.cpu_count() or 2,
        logger="bar"
    )

    try:

        final.close()

    except Exception:

        pass

    print(
        "DONE:",
        FINAL_VIDEO
    )

    return FINAL_VIDEO


if __name__ == "__main__":

    render()

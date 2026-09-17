
"""
Motivational Factory V6 Production Renderer

Purpose:
Create premium motivational Shorts from generated production briefs.

Pipeline:
production_brief.json
        |
        v
visual_assets.json
        |
        v
renderer.py
        |
        +--> cinematic asset selection
        +--> video/image composition
        +--> motion effects
        +--> captions hook
        +--> audio mixing
        |
        v
final_short.mp4


Expected files:
output/
    production_brief.json
    visual_assets.json
    caption_plan.json
    voice.wav
    music.mp3 (optional)
    sfx.wav (optional)

"""

import json
import math
import os
import requests
from pathlib import Path

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips,
    CompositeVideoClip,
    ColorClip,
    vfx
)


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

FINAL_VIDEO = OUTPUT / "final_short.mp4"


WIDTH = 1080
HEIGHT = 1920


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
    "meeting"
]


SYMBOLIC_KEYWORDS = {

    "discipline": [
        "mountain",
        "storm",
        "stone",
        "armor",
        "ancient"
    ],

    "wisdom": [
        "library",
        "statue",
        "manuscript",
        "ruins",
        "temple"
    ],

    "success": [
        "sunrise",
        "architecture",
        "city",
        "golden"
    ],

    "failure": [
        "dark",
        "rain",
        "broken",
        "storm"
    ],

    "growth": [
        "forest",
        "path",
        "light",
        "nature"
    ]
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

    target = OUTPUT / filename

    if target.exists():
        return target

    response = requests.get(
        url,
        timeout=60
    )

    response.raise_for_status()

    target.write_bytes(
        response.content
    )

    return target


# =====================================================
# ASSET INTELLIGENCE
# =====================================================

def score_asset(asset, scene):

    score = 0

    asset_text = json.dumps(
        asset
    ).lower()

    scene_text = json.dumps(
        scene
    ).lower()


    for bad in FORBIDDEN:

        if bad in asset_text:
            score -= 100


    for category, words in SYMBOLIC_KEYWORDS.items():

        if category in scene_text:

            for word in words:

                if word in asset_text:
                    score += 15


    duration = asset.get(
        "duration",
        0
    )

    if duration >= 5:
        score += 5


    if asset.get("width",0) >= 1080:
        score += 5


    return score



def choose_best_asset(scene, group):

    assets = []

    assets.extend(
        group.get("videos",[])
    )

    assets.extend(
        group.get("images",[])
    )


    if not assets:
        return None


    ranked = sorted(
        assets,
        key=lambda x: score_asset(
            x,
            scene
        ),
        reverse=True
    )


    return ranked[0]


# =====================================================
# VISUAL ENGINE
# =====================================================

def vertical_crop(clip):

    clip = clip.resize(
        height=HEIGHT
    )


    if clip.w < WIDTH:

        clip = clip.resize(
            width=WIDTH
        )


    return clip.crop(
        x_center=clip.w/2,
        y_center=clip.h/2,
        width=WIDTH,
        height=HEIGHT
    )



def ken_burns(image):

    duration = image.duration


    return image.resize(
        lambda t:
        1 + (0.04*t/duration)
    )



def create_scene(scene, asset):

    if not asset:

        return ColorClip(
            (WIDTH,HEIGHT),
            color=(0,0,0),
            duration=4
        )


    url = asset.get("url")


    if not url:

        return ColorClip(
            (WIDTH,HEIGHT),
            color=(0,0,0),
            duration=4
        )


    is_image = asset.get(
        "type"
    ) == "image"


    filename = (
        f"scene_{scene['scene']}.jpg"
        if is_image
        else
        f"scene_{scene['scene']}.mp4"
    )


    path = download(
        url,
        filename
    )


    if is_image:

        clip = ImageClip(
            str(path)
        ).set_duration(5)


        clip = vertical_crop(
            clip
        )

        return ken_burns(
            clip
        )


    clip = VideoFileClip(
        str(path)
    )


    clip = vertical_crop(
        clip
    )


    return clip.subclip(
        0,
        min(
            5,
            clip.duration
        )
    ).fx(
        vfx.fadein,
        0.5
    ).fx(
        vfx.fadeout,
        0.5
    )


# =====================================================
# AUDIO ENGINE
# =====================================================

def attach_audio(video):

    tracks = []


    voice = OUTPUT / "voice.wav"

    music = OUTPUT / "music.mp3"


    if voice.exists():

        tracks.append(
            AudioFileClip(
                str(voice)
            )
        )


    if music.exists():

        bg = AudioFileClip(
            str(music)
        ).volumex(
            0.18
        )

        tracks.append(
            bg
        )


    if tracks:

        video = video.set_audio(
            CompositeAudioClip(
                tracks
            )
        )


    return video



# =====================================================
# MAIN RENDER
# =====================================================

def render():

    print(
        "V6 Premium Renderer Starting"
    )


    brief = load_json(
        OUTPUT /
        "production_brief.json"
    )


    assets = load_json(
        OUTPUT /
        "visual_assets.json"
    )


    scenes = []


    for scene in brief.get(
        "scenes",
        []
    ):

        group = next(
            (
                x for x in assets
                if x.get("scene")
                ==
                scene.get("scene")
            ),
            {}
        )


        selected = choose_best_asset(
            scene,
            group
        )


        print(
            "Scene",
            scene.get("scene"),
            "selected:",
            selected
        )


        scenes.append(
            create_scene(
                scene,
                selected
            )
        )


    final = concatenate_videoclips(
        scenes,
        method="compose"
    )


    final = attach_audio(
        final
    )


    final.write_videofile(
        str(FINAL_VIDEO),
        fps=30,
        codec="libx264",
        audio_codec="aac",
        preset="medium"
    )


    print(
        "DONE:",
        FINAL_VIDEO
    )


if __name__ == "__main__":
    render()

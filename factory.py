import os
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime


from voice_engine import generate_voice
from caption_engine import create_caption_plan
from renderer import render



# =====================================
# MOTIVATIONAL VOICE PROFILE SYSTEM V5.4.1
# =====================================

VOICE_PROFILES = {

    "stoic_male": {
        "voice": "am_adam",
        "description": "Deep philosophical authority",
        "pace": "slow controlled delivery",
        "emotion": "calm conviction",
        "intensity": "medium",
        "pause_style": "strategic pauses after important ideas"
    },

    "power_male": {
        "voice": "am_michael",
        "description": "Powerful cinematic motivational narration",
        "pace": "controlled powerful delivery",
        "emotion": "determined intensity",
        "intensity": "high",
        "pause_style": "dramatic emphasis on key moments"
    },

    "warm_female": {
        "voice": "af_bella",
        "description": "Warm reflective inspirational narration",
        "pace": "natural expressive delivery",
        "emotion": "empathetic",
        "intensity": "medium",
        "pause_style": "gentle reflective pauses"
    },

    "hopeful_female": {
        "voice": "af_sarah",
        "description": "Hopeful transformation-focused narration",
        "pace": "uplifting cinematic delivery",
        "emotion": "optimistic",
        "intensity": "medium",
        "pause_style": "positive emotional pauses"
    }

}


DEFAULT_VOICE_PROFILE = "stoic_male"


def select_voice_profile(voice_direction):
    """Map the AI-selected personality to a configured Kokoro voice.

    Falls back safely to the configured default profile when the AI returns
    an unknown personality or malformed voice metadata.
    """
    if not isinstance(voice_direction, dict):
        voice_direction = {}

    personality = str(
        voice_direction.get("personality", "")
    ).strip().lower()

    profile = VOICE_PROFILES.get(
        personality,
        VOICE_PROFILES[DEFAULT_VOICE_PROFILE]
    )

    profile_name = (
        personality
        if personality in VOICE_PROFILES
        else DEFAULT_VOICE_PROFILE
    )

    return profile_name, profile


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


HISTORY_FILE = OUTPUT / "generation_history.json"


# =====================================
# GENERATION MEMORY
# Prevent repetitive AI outputs
# =====================================

def load_history():

    if not HISTORY_FILE.exists():
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return []


def save_history(data):

    history = load_history()

    history.append({

        "title":
        data.get("title", ""),

        "theme":
        data.get("theme", ""),

        "philosophical_theme":
        data.get(
            "creative_direction",
            {}
        ).get(
            "philosophical_theme",
            ""
        ),

        "visual_style":
        data.get(
            "creative_direction",
            {}
        ).get(
            "visual_style",
            ""
        ),

        "date":
        str(datetime.now())

    })

    # Keep only latest 20 generations
    history = history[-20:]

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            indent=2,
            ensure_ascii=False
        )


# =====================================
# CLOUDFLARE AI CINEMATIC DIRECTOR
# =====================================

def cloudflare_generate(feedback=""):

    account_id = os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]

    token = os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/"
        f"llama-3.1-8b-instruct"
    )

    history = load_history()

    previous_patterns = ""

    for item in history[-10:]:

        previous_patterns += (
            f"\n- Theme: {item.get('theme', '')}"
            f"\n- Style: {item.get('visual_style', '')}"
            f"\n- Archetype: {item.get('philosophical_theme', '')}\n"
        )

    payload = {

        "messages": [

            {

                "role": "system",

                "content": """
You are an expert motivational philosophy content director, cinematic short-form producer, and creative strategist.

As an expert motivational philosophy content director, every YouTube video script or content piece must incorporate a new, hooky, and interesting motivational philosophy to ensure compliance with YouTube policies and guidelines. Do not change other content aspects. Focus only on integrating fresh motivational philosophies to prevent repetitive or policy-risk content.

Your mission is to create premium motivational philosophy Shorts, not fictional stories.

Every video must introduce a fresh, hooky, and interesting motivational philosophy.
Avoid recycled quotes, generic advice lists, repeated templates, and minor variations of previous ideas.

Focus on:
- stoic principles
- mindset shifts
- discipline philosophies
- resilience concepts
- universal human insights

The viewer should experience a powerful idea, perspective shift, or realization rather than follow a character journey.

Automation should automate production, not creativity.

You are a professional cinematic motivational
film director, screenwriter, and creative producer.

Your job is NOT to generate repetitive AI content.

You create original short films for YouTube Shorts.

The final result must feel like a premium
human-created motivational documentary.

================================================

MAIN PRINCIPLE:

Automation should automate production,
not creativity.

Every generation must feel meaningfully different.

Change:

- story premise
- emotional journey
- conflict
- symbolism
- environment
- camera language
- visual identity
- ending lesson

================================================

ORIGINALITY RULES:

Never use:

- famous quotes
- celebrity speeches
- copied movie scenes
- existing stories
- recognizable copyrighted characters

Create original concepts.

================================================

NARRATION REQUIREMENTS:

Length:

70-150 words.

Must include:

1. Strong hook
2. Emotional tension
3. Transformation
4. Final memorable lesson

Do NOT create:

- quote collections
- generic advice lists
- motivational slogans

Write like a movie narrator.

================================================

VISUAL PHILOSOPHY:

Do NOT create literal stock footage scenes.

Do NOT force a random person to act the narration.

Instead:

Use symbolic cinematic storytelling.

The visual must communicate the
specific story beat and emotion.

Every scene must visually correspond
to what is happening in the narration.

If the narration describes:

- opening a door -> show the door being opened
- searching -> show searching
- sacrifice -> show an appropriate sacrifice
- isolation -> show isolation through composition
- discovery -> show the discovery
- struggle -> show the struggle

Do NOT simply place the protagonist
standing in front of the camera.

================================================

APPROVED CINEMATIC WORLDS:

STOIC PHILOSOPHY:

- ancient Roman architecture
- marble statues
- forgotten libraries
- philosophical manuscripts
- candlelit chambers
- marble halls
- ancient ruins

NATURE:

- mountains
- storms
- oceans
- forests
- deserts
- sunrise landscapes
- frozen landscapes

SYMBOLISM:

- broken chains
- old keys
- ancient books
- hourglass
- sword
- empty roads
- doors opening
- burning candles
- reflections

CINEMATIC ENVIRONMENTS:

- castles
- temples
- bridges
- dramatic corridors
- historical architecture
- luxury documentary locations

================================================

AVOID:

- random person standing
- person simply facing camera
- influencer lifestyle footage
- generic businessman clips
- fake crying scenes
- repetitive gym footage
- phone scrolling
- laptop typing
- generic office scenes

================================================

VISUAL QUALITY:

Every scene requires:

- meaningful subject
- specific story action
- emotion
- environment
- camera movement
- composition
- lighting

The action must be visually connected
to the corresponding narration line.

Think:

Netflix documentary +
luxury philosophy channel +
cinematic trailer.

================================================

VOICE DIRECTION:

Select the most suitable motivational narration profile.

Available profiles:

stoic_male:
Voice: am_adam
Use for philosophy, discipline, wisdom, self-control, and Stoic themes.

power_male:
Voice: am_michael
Use for resilience, sacrifice, warrior mindset, intensity, and achievement.

warm_female:
Voice: af_bella
Use for emotional reflection, healing, and personal growth.

hopeful_female:
Voice: af_sarah
Use for transformation, hope, and positive change.

Never imitate a real person.

Control:
- pacing
- pauses
- emotional delivery
- intensity
- emphasis on important philosophical phrases

The narration should sound like premium motivational Shorts content.



Choose delivery based on emotion.

Discipline:

deep,
controlled,
authoritative.

Healing:

warm,
reflective,
empathetic.

Transformation:

powerful,
cinematic,
determined.

================================================

IMPORTANT:

Every scene must have a distinct visual purpose.

Do not repeat the same composition
through all six scenes.

Do not make the main character appear
front-and-center in every scene.

Use:

- wide shots
- close-ups
- detail shots
- environmental shots
- over-the-shoulder shots
- silhouettes
- hands
- objects
- architectural framing
- symbolic compositions

when appropriate.

Return ONLY valid JSON.

No markdown.
"""

            },

            {

                "role": "user",

                "content": f"""
Create ONE unique cinematic motivational Short.

Previous generation patterns to avoid:

{previous_patterns}

Previous validation feedback:

{feedback}

Choose a unique combination.

Motivational philosophy direction:

- discipline journey
- failure transformation
- overcoming fear
- self discovery
- rebuilding after loss
- wisdom reflection
- sacrifice and achievement
- courage against uncertainty

Philosophical progression:

- darkness to light
- doubt to confidence
- chaos to discipline
- failure to growth
- weakness to strength
- confusion to purpose

Return exactly:

{{
    "title": "",
    "theme": "",
    "hook": "",
    "narration": "",

    "creative_direction": {{
        "philosophical_theme": "",
        "emotional_arc": "",
        "visual_style": "",
        "color_mood": "",
        "ending_style": ""
    }},

    "voice_direction": {{
        "personality": "",
        "pace": "",
        "emotion": "",
        "intensity": ""
    }},

    "background_queries": [
        "",
        "",
        ""
    ],

    "scenes": [
        {{
            "scene": 1,
            "voice_line": "",

            "visual": {{
                "type": "",
                "subject": "",
                "action": "",
                "emotion": "",
                "environment": "",
                "camera": "",
                "composition": "",
                "lighting": ""
            }},

            "pexels_query": "",
            "caption": ""
        }}
    ],

    "quality_score": {{
        "originality": 0,
        "philosophical_depth": 0,
        "visual_strength": 0,
        "repetition_risk": 0,
        "final_decision": ""
    }}
}}

Requirements:

- Create 5-8 cinematic visual moments. Do not force unnecessary scene changes.
- Narration 70-150 words.
- Every scene must feel cinematic.
- Every scene must correspond to its narration beat.
- Every scene must contain meaningful action or symbolic visual progression.
- Do not put the main character standing in front in every scene.
- Do not repeat the same visual composition.
- Use symbolic visuals where appropriate.
- Avoid repeated ideas from previous generations.
- Create original storytelling.
- quality_score may initially contain 0 values because the external quality gate will evaluate it later.
"""

            }

        ],

        "max_tokens": 3500
    }

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=120
    )

    response.raise_for_status()

    result = response.json().get("result")

    if isinstance(result, dict):

        return result.get(
            "response",
            result
        )

    return result


# =====================================
# JSON CLEANER
# =====================================

def parse_json(data):

    if isinstance(data, dict):
        return data

    text = str(data)

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        raise Exception("JSON not found")

    clean = match.group()

    # Remove invalid control characters
    clean = re.sub(
        r"[\x00-\x1f\x7f]",
        " ",
        clean
    )

    # Remove trailing commas
    clean = re.sub(
        r",\s*([}\]])",
        r"\1",
        clean
    )

    try:

        return json.loads(clean)

    except json.JSONDecodeError as e:

        print(
            "JSON repair attempt:",
            e
        )

        clean = clean.replace(
            "\\'",
            "'"
        )

        return json.loads(clean)


# =====================================
# CINEMATIC QUALITY VALIDATION
# =====================================

GENERIC_VISUAL_PATTERNS = [

    "random person",

    "person looking at camera",

    "businessman in office",

    "typing on laptop",

    "using phone",

    "influencer lifestyle",

    "selfie",

    "generic office worker",

    "social media influencer",

    "protagonist",

    "character journey",

    "he woke up",

    "she woke up"

]


def validate(data):

    required = [

        "title",
        "theme",
        "hook",
        "narration",
        "scenes",
        "background_queries",
        "creative_direction",
        "voice_direction"

    ]

    for item in required:

        if item not in data:

            print(
                "Missing field:",
                item
            )

            return False

    narration = data["narration"]

    if not isinstance(
        narration,
        str
    ):

        return False

    words = len(
        narration.split()
    )

    print(
        "Narration words:",
        words
    )

    if words < 70:

        print(
            "Narration too short"
        )

        return False

    if words > 170:

        print(
            "Narration too long"
        )

        return False

    scenes = data["scenes"]

    if not isinstance(
        scenes,
        list
    ):

        return False

    if len(scenes) < 5 or len(scenes) > 8:

        print(
            "Invalid scene count. Expected 5-8 cinematic visual moments."
        )

        return False

    for index, scene in enumerate(scenes, start=1):

        required_scene = [

            "scene",
            "voice_line",
            "visual",
            "pexels_query",
            "caption"

        ]

        for field in required_scene:

            if field not in scene:

                print(
                    "Missing scene field:",
                    field
                )

                return False

        visual = scene["visual"]

        if not isinstance(
            visual,
            dict
        ):

            return False

        visual_required = [

            "type",
            "subject",
            "action",
            "emotion",
            "environment",
            "camera",
            "composition",
            "lighting"

        ]

        for field in visual_required:

            if not visual.get(field):

                print(
                    "Missing visual:",
                    field
                )

                return False

        # =================================
        # Reject generic visuals
        # =================================

        combined = (

            visual["subject"]
            +
            visual["action"]
            +
            visual["environment"]

        ).lower()

        for bad in GENERIC_VISUAL_PATTERNS:

            if bad in combined:

                print(
                    "Generic visual rejected:",
                    bad
                )

                return False

    # =================================
    # Creative direction check
    # =================================

    creative = data[
        "creative_direction"
    ]

    if not isinstance(
        creative,
        dict
    ):

        return False

    for key in [

        "philosophical_theme",
        "emotional_arc",
        "visual_style",
        "color_mood",
        "ending_style"

    ]:

        if not creative.get(key):

            print(
                "Missing creative direction:",
                key
            )

            return False

    # =================================
    # Voice direction check
    # =================================

    voice = data[
        "voice_direction"
    ]

    if not isinstance(
        voice,
        dict
    ):

        return False

    for key in [

        "personality",
        "pace",
        "emotion",
        "intensity"

    ]:

        if not voice.get(key):

            print(
                "Missing voice direction:",
                key
            )

            return False

    print(
        "Cinematic validation passed"
    )

    return True


# =====================================
# V5.3 CREATIVE QUALITY GATE
# =====================================

QUALITY_MINIMUMS = {

    "originality": 7,
    "philosophical_depth": 7,
    "visual_strength": 7

}


def run_quality_gate(data):

    account_id = os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]

    token = os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/"
        f"llama-3.1-8b-instruct"
    )

    scenes_for_judge = []

    for scene in data.get("scenes", []):

        visual = scene.get(
            "visual",
            {}
        )

        scenes_for_judge.append({

            "scene": scene.get(
                "scene"
            ),

            "voice_line": scene.get(
                "voice_line"
            ),

            "subject": visual.get(
                "subject"
            ),

            "action": visual.get(
                "action"
            ),

            "emotion": visual.get(
                "emotion"
            ),

            "environment": visual.get(
                "environment"
            ),

            "camera": visual.get(
                "camera"
            ),

            "composition": visual.get(
                "composition"
            )

        })

    judge_payload = {

        "messages": [

            {

                "role": "system",

                "content": """
You are a strict cinematic creative quality judge.

Evaluate a generated motivational YouTube Short.

You are NOT rewriting the story.

You are judging whether it is creative enough
to continue into expensive production.

Score each category from 1 to 10.

originality:
Does the concept feel fresh and meaningfully
different from generic AI motivation?

philosophical_depth:
Does the story contain a believable emotional
journey rather than generic motivational advice?

visual_strength:
Do the scenes create strong cinematic imagery,
specific actions, environments and compositions?

repetition_risk:
How likely is the short to feel repetitive,
generic or interchangeable?

Important:

A high repetition_risk is BAD.

The final decision must be:

PASS

only when:

originality >= 7
philosophical_depth >= 7
visual_strength >= 7
repetition_risk <= 4

Otherwise:

REGENERATE

Return ONLY valid JSON.

Format:

{
    "originality": 0,
    "philosophical_depth": 0,
    "visual_strength": 0,
    "repetition_risk": 0,
    "final_decision": "PASS"
}
"""

            },

            {

                "role": "user",

                "content": json.dumps({

                    "title":
                    data.get(
                        "title",
                        ""
                    ),

                    "theme":
                    data.get(
                        "theme",
                        ""
                    ),

                    "hook":
                    data.get(
                        "hook",
                        ""
                    ),

                    "narration":
                    data.get(
                        "narration",
                        ""
                    ),

                    "creative_direction":
                    data.get(
                        "creative_direction",
                        {}
                    ),

                    "scenes":
                    scenes_for_judge

                }, ensure_ascii=False)

            }

        ],

        # Small judge response to reduce token usage
        "max_tokens": 500
    }

    response = requests.post(

        url,

        headers={

            "Authorization":
            f"Bearer {token}",

            "Content-Type":
            "application/json"

        },

        json=judge_payload,

        timeout=120

    )

    response.raise_for_status()

    result = response.json().get(
        "result"
    )

    if isinstance(result, dict):

        result = result.get(
            "response",
            result
        )

    quality = parse_json(
        result
    )

    if not isinstance(
        quality,
        dict
    ):

        raise Exception(
            "Quality gate returned invalid data"
        )

    try:

        originality = int(
            quality.get(
                "originality",
                0
            )
        )

        philosophical_depth = int(
            quality.get(
                "philosophical_depth",
                0
            )
        )

        visual_strength = int(
            quality.get(
                "visual_strength",
                0
            )
        )

        repetition_risk = int(
            quality.get(
                "repetition_risk",
                10
            )
        )

    except Exception:

        raise Exception(
            "Quality gate returned invalid scores"
        )

    # Clamp values safely to 1-10
    originality = max(
        1,
        min(10, originality)
    )

    philosophical_depth = max(
        1,
        min(10, philosophical_depth)
    )

    visual_strength = max(
        1,
        min(10, visual_strength)
    )

    repetition_risk = max(
        1,
        min(10, repetition_risk)
    )

    decision = "PASS"

    if originality < QUALITY_MINIMUMS["originality"]:

        decision = "REGENERATE"

    if philosophical_depth < QUALITY_MINIMUMS["philosophical_depth"]:

        decision = "REGENERATE"

    if visual_strength < QUALITY_MINIMUMS["visual_strength"]:

        decision = "REGENERATE"

    if repetition_risk > 4:

        decision = "REGENERATE"

    quality_result = {

        "originality":
        originality,

        "philosophical_depth":
        philosophical_depth,

        "visual_strength":
        visual_strength,

        "repetition_risk":
        repetition_risk,

        "final_decision":
        decision

    }

    # Save judge result into production brief
    data["quality_score"] = quality_result

    print(
        "Quality Score:"
    )

    print(
        f"  Originality: {originality}/10"
    )

    print(
        f"  Emotional Depth: {philosophical_depth}/10"
    )

    print(
        f"  Visual Strength: {visual_strength}/10"
    )

    print(
        f"  Repetition Risk: {repetition_risk}/10"
    )

    print(
        f"  Creative Decision: {decision}"
    )

    return decision == "PASS"


# =====================================
# PEXELS SEARCH
# =====================================

def _safe_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _video_candidate_score(video, target_duration=8):
    """Rank cinematic video candidates without changing the renderer."""
    width = _safe_number(video.get("width"))
    height = _safe_number(video.get("height"))
    duration = _safe_number(video.get("duration"))

    landscape_score = 1.0 if width > height else 0.0

    pixels = width * height
    if pixels >= 3840 * 2160:
        resolution_score = 1.0
    elif pixels >= 2560 * 1440:
        resolution_score = 0.92
    elif pixels >= 1920 * 1080:
        resolution_score = 0.82
    elif pixels > 0:
        resolution_score = min(
            0.75,
            pixels / (1920 * 1080) * 0.75
        )
    else:
        resolution_score = 0.0

    # Prefer longer usable cinematic clips while still allowing shorter clips.
    duration_score = min(
        1.0,
        max(0.0, duration / max(target_duration, 1))
    )

    # Prefer candidates with a high-quality preview picture.
    preview_score = 0.0
    for picture in video.get("video_pictures", []) or []:
        pw = _safe_number(picture.get("width"))
        ph = _safe_number(picture.get("height"))
        preview_pixels = pw * ph
        preview_score = max(
            preview_score,
            min(
                1.0,
                preview_pixels / (1920 * 1080)
            )
            if preview_pixels > 0 else 0.0
        )

    return (
        resolution_score * 0.40
        + duration_score * 0.30
        + landscape_score * 0.20
        + preview_score * 0.10
    )


def _select_best_video_file(video):
    """Pick the strongest landscape HD/4K source file."""
    files = video.get("video_files", []) or []

    candidates = []
    for file_item in files:
        width = _safe_number(file_item.get("width"))
        height = _safe_number(file_item.get("height"))

        if width <= 0 or height <= 0:
            continue

        landscape = width >= height
        quality = str(
            file_item.get("quality", "")
        ).lower()

        resolution_score = (
            min(
                1.0,
                (width * height) / (3840 * 2160)
            )
        )

        quality_bonus = 0.0
        if quality == "uhd":
            quality_bonus = 1.0
        elif quality == "hd":
            quality_bonus = 0.85

        score = (
            resolution_score * 0.75
            + quality_bonus * 0.15
            + (0.10 if landscape else 0.0)
        )

        candidates.append(
            (score, file_item)
        )

    if not candidates:
        return {}

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


def pexels_search(query):
    key = os.environ[
        "PEXELS_API_KEY"
    ]

    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={
                "Authorization":
                key
            },
            params={
                "query":
                query,

                # More candidates so the ranking logic can choose better footage.
                "per_page":
                20
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        ranked = []

        for video in data.get(
            "videos",
            []
        ):
            best_file = _select_best_video_file(video)

            candidate = {
                "id":
                video.get(
                    "id"
                ),

                "url":
                video.get(
                    "url"
                ),

                "duration":
                video.get(
                    "duration"
                ),

                "width":
                video.get(
                    "width"
                ),

                "height":
                video.get(
                    "height"
                ),

                "quality":
                best_file.get(
                    "quality"
                ),

                "video_file":
                best_file.get(
                    "link"
                ),

                "video_file_width":
                best_file.get(
                    "width"
                ),

                "video_file_height":
                best_file.get(
                    "height"
                ),

                "preview":
                (
                    (video.get("video_pictures") or [{}])[0]
                    .get("picture")
                )
            }

            candidate["_score"] = _video_candidate_score(
                video
            )

            ranked.append(
                candidate
            )

        ranked.sort(
            key=lambda item: item["_score"],
            reverse=True
        )

        results = []

        for candidate in ranked:
            candidate.pop(
                "_score",
                None
            )
            results.append(
                candidate
            )

        return results

    except Exception as e:
        print(
            "Pexels video search failed:",
            e
        )
        return []


def _image_candidate_score(photo):
    """Rank landscape photo candidates by resolution and preview quality."""
    width = _safe_number(photo.get("width"))
    height = _safe_number(photo.get("height"))

    landscape_score = 1.0 if width >= height else 0.0

    pixels = width * height
    resolution_score = min(
        1.0,
        pixels / (3840 * 2160)
    ) if pixels > 0 else 0.0

    src = photo.get(
        "src",
        {}
    )

    preview_score = 1.0 if src.get(
        "large2x"
    ) else (
        0.7 if src.get("large")
        else 0.0
    )

    return (
        resolution_score * 0.65
        + landscape_score * 0.25
        + preview_score * 0.10
    )


def pexels_image_search(query):
    key = os.environ[
        "PEXELS_API_KEY"
    ]

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={
                "Authorization":
                key
            },
            params={
                "query":
                query,

                "orientation":
                "landscape",

                "per_page":
                20
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        ranked = []

        for photo in data.get(
            "photos",
            []
        ):
            ranked.append(
                (
                    _image_candidate_score(photo),
                    {
                        "id":
                        photo.get(
                            "id"
                        ),

                        "url":
                        photo.get(
                            "url"
                        ),

                        "width":
                        photo.get(
                            "width"
                        ),

                        "height":
                        photo.get(
                            "height"
                        ),

                        "alt":
                        photo.get(
                            "alt"
                        ),

                        "image":
                        (
                            photo.get(
                                "src",
                                {}
                            ).get(
                                "original"
                            )
                        ),

                        "preview":
                        (
                            photo.get(
                                "src",
                                {}
                            ).get(
                                "large2x"
                            )
                        )
                    }
                )
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            item[1]
            for item in ranked
        ]

    except Exception as e:
        print(
            "Pexels image search failed:",
            e
        )
        return []


# =====================================
# MAIN PIPELINE
# =====================================

print(
    "Starting Motivational Factory V5.3"
)


final = None
last_error = ""


# =====================================
# GENERATION + STRUCTURAL VALIDATION
# + CREATIVE QUALITY GATE
# =====================================

for attempt in range(5):

    try:

        print(
            "Generation attempt",
            attempt + 1
        )

        raw = cloudflare_generate(
            last_error
        )

        data = parse_json(
            raw
        )

        # =================================
        # STEP 1:
        # Structural / cinematic validation
        # =================================

        if not validate(data):

            last_error = (
                "Structural validation failed. "
                "Create a valid cinematic original "
                "story with exactly 6 complete scenes "
                "and strong story-connected visuals."
            )

            print(
                "ERROR:",
                last_error
            )

            time.sleep(5)

            continue

        # =================================
        # STEP 2:
        # V5.3 Creative Quality Gate
        # =================================

        print(
            "Running V5.3 Creative Quality Gate..."
        )

        quality_passed = run_quality_gate(
            data
        )

        if not quality_passed:

            quality = data.get(
                "quality_score",
                {}
            )

            last_error = (

                "Creative Quality Gate rejected "
                "the previous generation. "

                f"Originality="
                f"{quality.get('originality', 0)}/10, "

                f"Emotional depth="
                f"{quality.get('philosophical_depth', 0)}/10, "

                f"Visual strength="
                f"{quality.get('visual_strength', 0)}/10, "

                f"Repetition risk="
                f"{quality.get('repetition_risk', 10)}/10. "

                "Create a substantially different "
                "cinematic concept. Avoid generic "
                "motivation, repeated visual structures, "
                "and interchangeable scenes. "
                "Make every scene directly support "
                "its narration beat."
            )

            print(
                "Creative Quality Gate: REGENERATE"
            )

            time.sleep(5)

            continue

        print(
            "Creative Quality Gate: PASS"
        )

        final = data

        break

    except Exception as e:

        print(
            "ERROR:",
            e
        )

        last_error = str(e)

        time.sleep(5)


if final is None:

    raise Exception(
        "Could not create valid high-quality cinematic Short"
    )


# =====================================
# SAVE PRODUCTION BRIEF
# =====================================


voice_profile_name, selected_voice_profile = select_voice_profile(
    final.get("voice_direction", {})
)

selected_voice = selected_voice_profile.get(
    "voice",
    "am_adam"
)

final["voice_profile_selected"] = {
    "profile":
    voice_profile_name,

    "voice":
    selected_voice,

    "description":
    selected_voice_profile.get(
        "description",
        ""
    ),

    "delivery": {
        "pace":
        final.get(
            "voice_direction",
            {}
        ).get(
            "pace",
            selected_voice_profile.get(
                "pace",
                ""
            )
        ),

        "emotion":
        final.get(
            "voice_direction",
            {}
        ).get(
            "emotion",
            selected_voice_profile.get(
                "emotion",
                ""
            )
        ),

        "intensity":
        final.get(
            "voice_direction",
            {}
        ).get(
            "intensity",
            selected_voice_profile.get(
                "intensity",
                ""
            )
        )
    }
}


with open(

    OUTPUT / "production_brief.json",

    "w",

    encoding="utf-8"

) as f:

    json.dump(

        final,

        f,

        indent=2,

        ensure_ascii=False

    )


print(
    "Production brief saved"
)


# =====================================
# PEXELS CINEMATIC ASSETS
# =====================================

assets = {
    "videos": [],
    "images": []
}


for scene in final["scenes"]:

    print(

        "Searching cinematic asset:",

        scene["pexels_query"]

    )

    videos = pexels_search(

        scene["pexels_query"]

    )

    images = pexels_image_search(

        scene["pexels_query"]

    )

    assets["videos"].append({

        "scene":
        scene["scene"],

        "visual":
        scene["visual"],

        "pexels_query":
        scene["pexels_query"],

        "videos":
        videos

    })

    assets["images"].append({

        "scene":
        scene["scene"],

        "visual":
        scene["visual"],

        "pexels_query":
        scene["pexels_query"],

        "images":
        images

    })


with open(

    OUTPUT / "visual_assets.json",

    "w",

    encoding="utf-8"

) as f:

    json.dump(

        assets,

        f,

        indent=2,

        ensure_ascii=False

    )


print(
    "Visual assets saved"
)


# =====================================
# VOICE GENERATION
# =====================================

narration = final["narration"]

print(
    "Generating cinematic voice with profile:",
    voice_profile_name,
    "->",
    selected_voice
)


try:

    generate_voice(
        narration,
        voice_profile=selected_voice
    )

except Exception as voice_error:

    print(
        "Selected voice failed:",
        voice_error
    )

    print(
        "Falling back to am_adam..."
    )

    generate_voice(
        narration,
        voice_profile="am_adam"
    )


print(
    "Voice completed"
)


# =====================================
# CAPTION GENERATION
# =====================================

print(
    "Creating caption plan..."
)


create_caption_plan(
    narration
)


print(
    "Caption plan completed"
)


# =====================================
# SAVE GENERATION MEMORY
# =====================================

save_history(
    final
)


print(
    """
=================================

MOTIVATIONAL FACTORY V5.3 COMPLETE

Generated:

✓ Production Brief
✓ Cinematic Visual Plan
✓ Creative Quality Gate
✓ Quality Score
✓ Pexels Assets
✓ Kokoro Voice
✓ Caption Plan
✓ Creative History

Quality Gate:

✓ Originality checked
✓ Emotional depth checked
✓ Visual strength checked
✓ Repetition risk checked

Ready for:

V6 VIDEO RENDERER

=================================
"""
)

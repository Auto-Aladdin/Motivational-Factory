import os
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime


from voice_engine import generate_voice
from caption_engine import create_caption_plan


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

                "per_page":
                5

            },

            timeout=30

        )

        response.raise_for_status()

        data = response.json()

        results = []

        for video in data.get(
            "videos",
            []
        ):

            results.append({

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
                )

            })

        return results

    except Exception as e:

        print(
            "Pexels search failed:",
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

assets = []


for scene in final["scenes"]:

    print(

        "Searching cinematic asset:",

        scene["pexels_query"]

    )

    videos = pexels_search(

        scene["pexels_query"]

    )

    assets.append({

        "scene":
        scene["scene"],

        "visual":
        scene["visual"],

        "pexels_query":
        scene["pexels_query"],

        "videos":
        videos

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
    "Generating cinematic voice..."
)


generate_voice(
    narration
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

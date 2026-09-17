import os
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime

from voice_engine import generate_voice
from caption_engine import create_caption_plan


# =====================================
# OUTPUT
# =====================================

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
            data = json.load(f)

        if isinstance(data, list):
            return data

        return []

    except Exception:
        return []


def save_history(data):
    history = load_history()

    creative_direction = data.get(
        "creative_direction",
        {}
    )

    history.append({
        "title": data.get("title", ""),
        "theme": data.get("theme", ""),
        "story_archetype": creative_direction.get(
            "story_archetype",
            ""
        ),
        "visual_style": creative_direction.get(
            "visual_style",
            ""
        ),
        "date": str(datetime.now())
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

    # =================================
    # Load previous creative history
    # =================================

    history = load_history()

    previous_patterns = ""

    for item in history[-10:]:
        previous_patterns += (
            f"\n- Theme: {item.get('theme', '')}"
            f"\n- Style: {item.get('visual_style', '')}"
            f"\n- Archetype: {item.get('story_archetype', '')}\n"
        )

    # =================================
    # Cloudflare payload
    # =================================

    payload = {
        "messages": [
            {
                "role": "system",
                "content": """
You are a professional cinematic motivational
film director, screenwriter, and creative producer.

Your job is NOT to generate repetitive AI content.

You create original short films for YouTube Shorts.

The final result must feel like a premium
human-created motivational documentary.

================================================
MAIN PRINCIPLE
================================================

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
ORIGINALITY RULES
================================================

Never use:

- famous quotes
- celebrity speeches
- copied movie scenes
- existing stories
- recognizable copyrighted characters

Create original concepts.

================================================
NARRATION REQUIREMENTS
================================================

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
VISUAL PHILOSOPHY
================================================

Every scene must visually communicate
the specific story beat being narrated.

Do NOT create generic stock footage.

Do NOT simply place a random person
standing in front of the camera.

Do NOT make the main character appear
in every scene doing nothing.

The visual must show a meaningful action,
event, interaction, or symbolic transformation.

If narration says someone opens a door,
the visual must show the person opening
the door.

If narration says someone discovers a book,
the visual must show the discovery.

If narration introduces another character,
that character must appear in the scene.

The scene must make sense even without narration.

Use cinematic storytelling.

================================================
APPROVED CINEMATIC WORLDS
================================================

STOIC PHILOSOPHY:

- Marcus Aurelius inspired marble statues
- ancient Roman architecture
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
AVOID
================================================

- random person standing
- person simply looking at camera
- influencer lifestyle footage
- generic businessman clips
- generic office footage
- fake crying scenes
- repetitive gym footage
- phone scrolling
- laptop typing
- empty character portraits
- character standing with nothing happening

================================================
VISUAL QUALITY
================================================

Every scene requires:

- meaningful subject
- specific action
- emotion
- environment
- camera movement
- composition
- lighting

Most importantly:

ACTION MUST MATCH THE STORY BEAT.

Do not write an action that is unrelated
to the narration.

Think:

Netflix documentary +
luxury philosophy channel +
cinematic trailer.

================================================
VOICE DIRECTION
================================================

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
JSON RULES
================================================

Return ONLY valid JSON.

No markdown.

No explanations.

The JSON must contain exactly 6 scenes.

Each scene must contain complete visual metadata.

Every scene must be meaningfully different
from the other scenes.
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

================================================
STORY ARCHETYPE
================================================

Choose one:

- discipline journey
- failure transformation
- overcoming fear
- self discovery
- rebuilding after loss
- wisdom reflection
- sacrifice and achievement
- courage against uncertainty

================================================
EMOTIONAL JOURNEY
================================================

Choose one:

- darkness to light
- doubt to confidence
- chaos to discipline
- failure to growth
- weakness to strength
- confusion to purpose

================================================
IMPORTANT SCENE RULE
================================================

Create a visual progression.

Do NOT make the same main character
simply stand in front of the camera
in every scene.

Each scene must show a specific action
connected to its voice_line.

If another character is mentioned,
show that character.

If a manager, teacher, mentor, friend,
parent, opponent, or other person is
important to the story, include them
visually when appropriate.

The six scenes should work together
as one continuous visual story.

================================================
RETURN EXACTLY THIS STRUCTURE
================================================

{{
    "title": "",
    "theme": "",
    "hook": "",
    "narration": "",

    "creative_direction": {{
        "story_archetype": "",
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
        }},
        {{
            "scene": 2,
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
        }},
        {{
            "scene": 3,
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
        }},
        {{
            "scene": 4,
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
        }},
        {{
            "scene": 5,
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
        }},
        {{
            "scene": 6,
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
    ]
}}

================================================
FINAL REQUIREMENTS
================================================

- Exactly 6 scenes.
- Narration must be 70-150 words.
- Every scene must feel cinematic.
- Every scene must contain a meaningful action.
- Every action must match its voice_line.
- Use symbolic visuals where appropriate.
- Avoid generic visuals.
- Avoid repetitive scenes.
- Create original storytelling.
- Maintain visual continuity where characters return.
- Introduce secondary characters when the story requires them.
- Do not put the main character in front doing nothing.
"""
            }
        ],
        "max_tokens": 3500
    }

    # =================================
    # API REQUEST
    # =================================

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

    response_data = response.json()

    result = response_data.get("result")

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

    if data is None:
        raise Exception("AI returned empty response")

    text = str(data).strip()

    # Remove markdown JSON fences
    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```JSON",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    text = text.strip()

    # ---------------------------------
    # Find JSON object
    # ---------------------------------

    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        raise Exception("JSON not found in AI response")

    clean = match.group()

    # ---------------------------------
    # Remove invalid control characters
    # ---------------------------------

    clean = re.sub(
        r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
        " ",
        clean
    )

    # ---------------------------------
    # Remove trailing commas
    # ---------------------------------

    clean = re.sub(
        r",\s*([}\]])",
        r"\1",
        clean
    )

    # ---------------------------------
    # First JSON parse
    # ---------------------------------

    try:
        return json.loads(clean)

    except json.JSONDecodeError as first_error:

        print(
            "JSON decode failed:",
            first_error
        )

        # ---------------------------------
        # Second repair pass
        # ---------------------------------

        repaired = clean.replace(
            "\\'",
            "'"
        )

        repaired = re.sub(
            r",\s*([}\]])",
            r"\1",
            repaired
        )

        try:
            return json.loads(repaired)

        except json.JSONDecodeError as second_error:
            raise Exception(
                f"Could not parse AI JSON: {second_error}"
            ) from second_error


# =====================================
# CINEMATIC QUALITY VALIDATION
# =====================================

GENERIC_VISUAL_WORDS = [
    "person standing",
    "person simply standing",
    "man standing",
    "woman standing",
    "person looking at camera",
    "looking at camera",
    "businessman",
    "generic businessman",
    "office",
    "laptop",
    "phone scrolling",
    "influencer",
    "influencer lifestyle"
]


GENERIC_ACTION_WORDS = [
    "standing",
    "stands",
    "stand still",
    "looking at camera",
    "looks at camera"
]


def validate(data):

    # =================================
    # Top-level required fields
    # =================================

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

    if not isinstance(data, dict):
        print("AI output is not a JSON object")
        return False

    for item in required:

        if item not in data:
            print(
                "Missing field:",
                item
            )
            return False

    # =================================
    # Narration validation
    # =================================

    narration = data["narration"]

    if not isinstance(
        narration,
        str
    ):
        print("Narration is not a string")
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

    if words > 150:
        print(
            "Narration too long"
        )
        return False

    # =================================
    # Background query validation
    # =================================

    background_queries = data[
        "background_queries"
    ]

    if not isinstance(
        background_queries,
        list
    ):
        print(
            "background_queries must be a list"
        )
        return False

    if len(background_queries) < 3:
        print(
            "Not enough background queries"
        )
        return False

    # =================================
    # Scene validation
    # =================================

    scenes = data["scenes"]

    if not isinstance(
        scenes,
        list
    ):
        print(
            "Scenes must be a list"
        )
        return False

    if len(scenes) != 6:
        print(
            "Wrong scene count:",
            len(scenes)
        )
        return False

    # =================================
    # Validate every scene
    # =================================

    for index, scene in enumerate(
        scenes,
        start=1
    ):

        if not isinstance(
            scene,
            dict
        ):
            print(
                "Invalid scene:",
                index
            )
            return False

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
                    field,
                    "in scene",
                    index
                )
                return False

        # ---------------------------------
        # Scene number
        # ---------------------------------

        if scene.get("scene") != index:
            print(
                "Incorrect scene number:",
                scene.get("scene")
            )
            return False

        # ---------------------------------
        # Voice line
        # ---------------------------------

        if not isinstance(
            scene.get("voice_line"),
            str
        ) or not scene.get(
            "voice_line"
        ).strip():

            print(
                "Missing voice line in scene:",
                index
            )
            return False

        # ---------------------------------
        # Visual object
        # ---------------------------------

        visual = scene["visual"]

        if not isinstance(
            visual,
            dict
        ):
            print(
                "Visual is not an object in scene:",
                index
            )
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
                    field,
                    "in scene:",
                    index
                )

                return False

        # ---------------------------------
        # Reject generic visuals
        # ---------------------------------

        combined = " ".join([
            str(visual.get("type", "")),
            str(visual.get("subject", "")),
            str(visual.get("action", "")),
            str(visual.get("emotion", "")),
            str(visual.get("environment", ""))
        ]).lower()

        for bad in GENERIC_VISUAL_WORDS:

            if bad in combined:

                print(
                    "Generic visual rejected:",
                    bad,
                    "scene:",
                    index
                )

                return False

        # ---------------------------------
        # Reject empty/non-meaningful action
        # ---------------------------------

        action = str(
            visual.get("action", "")
        ).strip().lower()

        if action in GENERIC_ACTION_WORDS:

            print(
                "Generic action rejected:",
                action,
                "scene:",
                index
            )

            return False

        # ---------------------------------
        # Pexels query
        # ---------------------------------

        if not isinstance(
            scene.get("pexels_query"),
            str
        ) or not scene.get(
            "pexels_query"
        ).strip():

            print(
                "Missing Pexels query in scene:",
                index
            )

            return False

        # ---------------------------------
        # Caption
        # ---------------------------------

        if not isinstance(
            scene.get("caption"),
            str
        ):

            print(
                "Invalid caption in scene:",
                index
            )

            return False

    # =================================
    # Creative direction validation
    # =================================

    creative = data[
        "creative_direction"
    ]

    if not isinstance(
        creative,
        dict
    ):
        print(
            "Invalid creative_direction"
        )
        return False

    creative_required = [
        "story_archetype",
        "emotional_arc",
        "visual_style",
        "color_mood",
        "ending_style"
    ]

    for key in creative_required:

        if not creative.get(key):

            print(
                "Missing creative direction:",
                key
            )

            return False

    # =================================
    # Voice direction validation
    # =================================

    voice = data[
        "voice_direction"
    ]

    if not isinstance(
        voice,
        dict
    ):
        print(
            "Invalid voice_direction"
        )
        return False

    voice_required = [
        "personality",
        "pace",
        "emotion",
        "intensity"
    ]

    for key in voice_required:

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
# PEXELS SEARCH
# =====================================

def pexels_search(query):

    key = os.environ[
        "PEXELS_API_KEY"
    ]

    if not query:
        return []

    try:

        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={
                "Authorization": key
            },
            params={
                "query": query,
                "per_page": 5
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
                "id": video.get(
                    "id"
                ),
                "url": video.get(
                    "url"
                ),
                "duration": video.get(
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

def main():

    print(
        "Starting Motivational Factory V5.2"
    )

    final = None
    last_error = ""

    # =================================
    # AI GENERATION RETRIES
    # =================================

    for attempt in range(3):

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

            if validate(data):

                final = data

                break

            last_error = (
                "Validation failed. "
                "Create a more cinematic original "
                "story with stronger scene actions. "
                "Every visual must directly match "
                "its narration and every scene must "
                "contain meaningful activity."
            )

            raise Exception(
                "Validation failed"
            )

        except Exception as e:

            print(
                "ERROR:",
                e
            )

            last_error = str(e)

            if attempt < 2:
                time.sleep(5)

    # =================================
    # Final validation result
    # =================================

    if final is None:

        raise Exception(
            "Could not create valid cinematic Short"
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

        scene_number = scene["scene"]
        pexels_query = scene["pexels_query"]

        print(
            f"Searching cinematic asset "
            f"for scene {scene_number}: "
            f"{pexels_query}"
        )

        videos = pexels_search(
            pexels_query
        )

        assets.append({
            "scene": scene_number,
            "visual": scene["visual"],
            "voice_line": scene["voice_line"],
            "pexels_query": pexels_query,
            "videos": videos
        })

    # =====================================
    # SAVE VISUAL ASSETS
    # =====================================

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
        "Generation history saved"
    )

    # =====================================
    # COMPLETE
    # =====================================

    print(
        """
=================================

MOTIVATIONAL FACTORY V5.2 COMPLETE

Generated:

✓ Production Brief
✓ Cinematic Visual Plan
✓ Pexels Assets
✓ Kokoro Voice
✓ Caption Plan
✓ Creative History

Ready for:

V6 VIDEO RENDERER

=================================
"""
    )


# =====================================
# ENTRY POINT
# =====================================

if __name__ == "__main__":
    main()

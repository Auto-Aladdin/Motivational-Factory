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
        data.get("title",""),

        "theme":
        data.get("theme",""),

        "story_archetype":
        data.get(
            "creative_direction",
            {}
        ).get(
            "story_archetype",
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

            f"\n- Theme: {item.get('theme')}"

            f"\n- Style: {item.get('visual_style')}"

            f"\n- Archetype: {item.get('story_archetype')}\n"

        )





    payload = {


        "messages":[


            {


                "role":"system",

                "content":"""

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

70-150 words


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

The visual should represent the emotion.

================================================

APPROVED CINEMATIC WORLDS:


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

AVOID:

- random person standing
- influencer lifestyle footage
- generic businessman clips
- fake crying scenes
- repetitive gym footage
- phone scrolling
- laptop typing


================================================

VISUAL QUALITY:

Every scene requires:

- meaningful subject
- action
- emotion
- environment
- camera movement
- composition
- lighting


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

Return ONLY valid JSON.

No markdown.

"""

            },


            {


                "role":"user",

                "content":f"""

Create ONE unique cinematic motivational Short.


Previous generation patterns to avoid:

{previous_patterns}


Previous validation feedback:

{feedback}


Choose a unique combination:


Story archetype:

- discipline journey
- failure transformation
- overcoming fear
- self discovery
- rebuilding after loss
- wisdom reflection
- sacrifice and achievement
- courage against uncertainty


Emotional journey:

- darkness to light
- doubt to confidence
- chaos to discipline
- failure to growth
- weakness to strength
- confusion to purpose



Return exactly:


{{
"title":"",

"theme":"",

"hook":"",

"narration":"",


"creative_direction":{{

"story_archetype":"",

"emotional_arc":"",

"visual_style":"",

"color_mood":"",

"ending_style":""


}},


"voice_direction":{{

"personality":"",

"pace":"",

"emotion":"",

"intensity":""


}},


"background_queries":[

"",

"",

""

],


"scenes":[

{{

"scene":1,

"voice_line":"",


"visual":{{

"type":"",

"subject":"",

"action":"",

"emotion":"",

"environment":"",

"camera":"",

"composition":"",

"lighting":""


}},


"pexels_query":"",

"caption":""


}}

]

}}


Requirements:

- Exactly 6 scenes.
- Narration 70-150 words.
- Every scene must feel cinematic.
- Use symbolic visuals.
- Avoid repeated ideas.
- Create original storytelling.


"""

            }

        ],


        "max_tokens":3500

    }



    response = requests.post(

        url,

        headers={

            "Authorization":
            f"Bearer {token}",


            "Content-Type":
            "application/json"

        },

        json=payload,

        timeout=120

    )



    response.raise_for_status()



    result = response.json().get(
        "result"
    )



    if isinstance(result,dict):

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

        raise Exception(
            "JSON not found"
        )



    clean = match.group()



    # Remove invalid characters

    clean = re.sub(

        r'[\x00-\x1f\x7f]',

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

        return json.loads(
            clean
        )


    except json.JSONDecodeError as e:


        print(
            "JSON repair attempt:",
            e
        )


        clean = clean.replace(
            "\\'",
            "'"
        )



        return json.loads(
            clean
        )





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

    "social media influencer"

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



    if len(scenes) != 6:


        print(

            "Wrong scene count"

        )


        return False





    for scene in scenes:



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





        # ==========================
        # Reject generic visuals
        # ==========================


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





    # ==========================
    # Creative direction check
    # ==========================


    creative = data[

        "creative_direction"

    ]



    for key in [

        "story_archetype",

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





    # ==========================
    # Voice direction check
    # ==========================


    voice = data[

        "voice_direction"

    ]



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

    "Starting Motivational Factory V5.2"

)





final = None


last_error = ""





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

            "story with stronger visuals."

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



        time.sleep(5)







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

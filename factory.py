import os
import json
import re
import time
import requests
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



# ==========================================
# CLOUDFLARE AI REQUEST
# ==========================================

def cloudflare_request(messages, max_tokens=4000):

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]


    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )


    response = requests.post(

        url,

        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },

        json={
            "messages": messages,
            "max_tokens": max_tokens
        },

        timeout=120
    )


    response.raise_for_status()


    result=response.json()["result"]


    if isinstance(result,dict):

        return result.get(
            "response",
            result
        )


    return result





# ==========================================
# STORY DIRECTOR GENERATION
# ==========================================

def generate_short():


    messages=[


    {
    "role":"system",
    "content":"""

You are an elite motivational Shorts director,
screenwriter and visual storyteller.

Create a complete cinematic short video blueprint.

The video must feel like a real motivational film,
not a quote slideshow.

Requirements:

Narration:
- 90-130 words
- Strong first sentence hook
- Emotional journey
- Clear lesson
- Powerful ending

Story structure:

1 Hook
2 Struggle
3 Internal conflict
4 Realization
5 Action
6 Transformation


Create ONE main protagonist.

Character consistency:

Define:

- name
- age
- appearance
- clothing style
- personality

Every scene must use the same person.


Visual direction:

Every scene requires:

subject
action
emotion
environment
camera
lighting
visual_style


Important:

The visual must show the exact narration moment.

Do not create:
- random inspirational images
- people simply standing
- unrelated scenery


Pexels queries:

Create simple searchable keywords.

Example:

Bad:
"lonely entrepreneur facing his deepest fears"

Good:
"person working alone office night"


Return ONLY JSON.

"""
    },


    {
    "role":"user",
    "content":"""

Create a motivational Short.

Choose a unique topic:

discipline
failure
confidence
fear
dreams
success
consistency
hard work
personal growth
resilience


Return exactly:

{

"title":"",
"theme":"",
"hook":"",

"character":{

"name":"",
"age":"",
"appearance":"",
"clothing":"",
"personality":""

},


"narration":"",


"scenes":[

{

"scene":1,

"voice_line":"",

"visual":{

"subject":"",
"action":"",
"emotion":"",
"environment":"",
"camera":"",
"lighting":"",
"visual_style":""

},

"pexels_query":"",

"caption":""

}

]

}


Create exactly 6 scenes.

"""
    }

    ]


    return cloudflare_request(
        messages
    )





# ==========================================
# NARRATION REPAIR
# ==========================================

def repair_narration(text):


    print(
        "Repairing narration..."
    )


    messages=[

    {
    "role":"system",
    "content":"""

Rewrite this motivational narration.

Rules:

- Keep the same meaning
- Make it emotional
- Make it cinematic
- 90-130 words
- Strong ending

Return only narration.

"""
    },


    {
    "role":"user",
    "content":text
    }

    ]


    return str(
        cloudflare_request(
            messages,
            800
        )
    )





# ==========================================
# JSON CLEANER
# ==========================================

def parse_json(data):


    if isinstance(data,dict):

        return data


    text=str(data)


    text=text.replace(
        "```json",
        ""
    )


    text=text.replace(
        "```",
        ""
    )


    match=re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )


    if not match:

        raise Exception(
            "JSON missing"
        )


    return json.loads(
        match.group()
    )





# ==========================================
# VALIDATION
# ==========================================

def validate(data):


    required=[
        "title",
        "theme",
        "character",
        "narration",
        "scenes"
    ]


    for item in required:

        if item not in data:

            print(
                "Missing",
                item
            )

            return False



    words=len(
        data["narration"].split()
    )


    print(
        "Narration:",
        words
    )


    if words < 25:

        return False


    if len(data["scenes"]) != 6:

        return False



    character=data["character"]


    for key in [
        "name",
        "age",
        "appearance",
        "clothing",
        "personality"
    ]:

        if not character.get(key):

            return False



    for scene in data["scenes"]:


        visual=scene.get(
            "visual",
            {}
        )


        for key in [

            "subject",
            "action",
            "emotion",
            "environment",
            "camera",
            "lighting",
            "visual_style"

        ]:


            if not visual.get(key):

                return False



        if not scene.get(
            "pexels_query"
        ):

            return False



    return True





# ==========================================
# PEXELS
# ==========================================

def pexels_search(query):


    key=os.environ["PEXELS_API_KEY"]


    response=requests.get(

        "https://api.pexels.com/videos/search",

        headers={
            "Authorization":key
        },

        params={

            "query":query,

            "per_page":3

        },

        timeout=30
    )


    response.raise_for_status()


    data=response.json()


    videos=[]


    for video in data.get(
        "videos",
        []
    ):

        videos.append({

            "id":video["id"],

            "url":video["url"]

        })


    return videos





# ==========================================
# MAIN
# ==========================================


print(
"Starting Motivational Factory V4"
)


final=None



for attempt in range(5):


    try:


        print(
            "Attempt",
            attempt+1
        )


        raw=generate_short()


        data=parse_json(raw)



        if validate(data):


            if len(
                data["narration"].split()
            ) < 90:


                data["narration"]=repair_narration(
                    data["narration"]
                )


            final=data

            break



    except Exception as e:


        print(
            "ERROR:",
            e
        )


    time.sleep(5)





if final is None:


    raise Exception(
        "Could not create Short"
    )





with open(

    OUTPUT/"short_plan.json",

    "w",

    encoding="utf-8"

) as f:


    json.dump(

        final,

        f,

        indent=2,

        ensure_ascii=False

    )





assets=[]



for scene in final["scenes"]:


    assets.append({

        "scene":scene["scene"],

        "character":final["character"],

        "visual":scene["visual"],

        "query":scene["pexels_query"],

        "videos":pexels_search(
            scene["pexels_query"]
        )

    })





with open(

    OUTPUT/"visual_assets.json",

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
"FACTORY V4 COMPLETE"
)

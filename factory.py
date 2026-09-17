import os
import json
import re
import time
import requests
from pathlib import Path


from voice_engine import generate_voice
from caption_engine import create_caption_plan



OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



# =====================================
# CLOUDFLARE AI GENERATION
# =====================================

def cloudflare_generate():


    account_id = os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]


    token = os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]



    url = (

        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"

    )



    payload = {


        "messages":[


            {


                "role":"system",


                "content":"""

You are a professional motivational short film director.

Create original motivational videos for YouTube Shorts.

Rules:

- Create a complete story.
- Narration must be 70-150 words.
- Strong first sentence hook.
- Emotional progression.
- Clear transformation.
- Powerful ending.
- No famous quotes.
- No copied phrases.

Visual direction:

Every scene must match the narration.

Describe:

subject
action
emotion
environment
camera style


Return ONLY valid JSON.

"""

            },


            {


                "role":"user",


                "content":"""

Create one motivational short.

Choose a unique topic:

discipline,
failure,
confidence,
fear,
success,
growth,
consistency,
dreams,
hard work,
self belief


Return exactly:

{
"title":"",
"theme":"",
"hook":"",
"narration":"",
"background_queries":[
"",
"",
""
],

"scenes":[

{
"scene":1,

"voice_line":"",

"visual":{
"subject":"",
"action":"",
"emotion":"",
"environment":"",
"camera":""
},

"pexels_query":"",
"caption":""

}

]

}


Create exactly 6 scenes.

"""

            }

        ],


        "max_tokens":3500

    }




    response=requests.post(


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



    data=response.json()



    result=data.get(
        "result"
    )



    if isinstance(
        result,
        dict
    ):

        if "response" in result:

            return result["response"]


    return result





# =====================================
# JSON CLEANER
# =====================================

def parse_json(data):


    if isinstance(
        data,
        dict
    ):

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
            "JSON not found"
        )



    clean=match.group()



    # Remove invalid characters

    clean=clean.replace(
        "\n",
        " "
    )


    clean=clean.replace(
        "\r",
        " "
    )


    clean=clean.replace(
        "\t",
        " "
    )



    return json.loads(
        clean
    )





# =====================================
# VALIDATION
# =====================================

def validate(data):


    required=[

        "title",
        "theme",
        "hook",
        "narration",
        "scenes",
        "background_queries"

    ]



    for item in required:

        if item not in data:

            print(
                "Missing:",
                item
            )

            return False



    words=len(

        data["narration"].split()

    )



    print(
        "Narration words:",
        words
    )



    if words < 50:

        print(
            "Narration too short"
        )

        return False



    scenes=data["scenes"]



    if len(scenes)!=6:

        print(
            "Wrong scene count"
        )

        return False




    for scene in scenes:


        if "visual" not in scene:

            return False



        visual=scene["visual"]



        for key in [

            "subject",
            "action",
            "emotion",
            "environment",
            "camera"

        ]:


            if not visual.get(key):

                print(
                    "Missing visual:",
                    key
                )

                return False



    return True





# =====================================
# PEXELS SEARCH
# =====================================

def pexels_search(query):


    key=os.environ[
        "PEXELS_API_KEY"
    ]



    response=requests.get(

        "https://api.pexels.com/videos/search",

        headers={

            "Authorization":
            key

        },

        params={

            "query":query,

            "per_page":3

        },

        timeout=30

    )



    response.raise_for_status()



    data=response.json()



    results=[]



    for video in data.get(
        "videos",
        []
    ):


        results.append({

            "id":
            video["id"],

            "url":
            video["url"]

        })



    return results





# =====================================
# MAIN PIPELINE
# =====================================


print(
"Starting Motivational Factory V5"
)



final=None



for attempt in range(3):


    try:


        print(

            "Generation attempt",

            attempt+1

        )



        raw=cloudflare_generate()



        data=parse_json(
            raw
        )



        if validate(data):


            final=data

            break



        raise Exception(
            "Validation failed"
        )



    except Exception as e:


        print(
            "ERROR:",
            e
        )


        time.sleep(5)





if final is None:


    raise Exception(

        "Could not create valid Short"

    )





# =====================================
# SAVE PLAN
# =====================================


with open(

    OUTPUT/"production_brief.json",

    "w",

    encoding="utf-8"

) as f:


    json.dump(

        final,

        f,

        indent=2,

        ensure_ascii=False

    )





# =====================================
# PEXELS ASSETS
# =====================================


assets=[]



for scene in final["scenes"]:


    print(

        "Searching Pexels:",

        scene["pexels_query"]

    )



    assets.append({

        "scene":

        scene["scene"],


        "visual":

        scene["visual"],


        "videos":

        pexels_search(

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





# =====================================
# VOICE + CAPTIONS
# =====================================


narration=final["narration"]



generate_voice(
    narration
)



create_caption_plan(
    narration
)



print(
"FACTORY V5 + VOICE ENGINE COMPLETE"
)

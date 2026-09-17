import os
import json
import re
import time
import requests
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



# =====================================
# CLOUDFLARE AI
# =====================================

def cloudflare_request(messages, max_tokens=3500):

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

    data=response.json()

    result=data["result"]


    if isinstance(result, dict):

        return result.get(
            "response",
            result
        )


    return result





def cloudflare_generate():


    messages=[

    {
    "role":"system",
    "content":"""

You are a professional motivational Shorts writer.

Create cinematic motivational videos.

IMPORTANT:

The narration must be between 90 and 130 words.

Do not create short quotes.
Do not summarize.
Write a complete spoken narration.

The narration should contain:

- powerful opening hook
- struggle
- emotional realization
- lesson
- transformation
- memorable ending

Create exactly 6 scenes.

Every scene must visually represent the exact spoken line.

Return ONLY JSON.

"""
    },


    {
    "role":"user",
    "content":"""

Create a unique motivational Short.

Topic examples:

discipline,
failure,
fear,
success,
dreams,
confidence,
consistency,
personal growth.

Avoid common repeated motivational phrases.

JSON format:

{
"title":"",
"theme":"",
"hook":"",
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
"camera":""
},
"pexels_query":"",
"caption":""
}

]

}

"""
    }

    ]


    return cloudflare_request(messages)




# =====================================
# NARRATION REPAIR
# =====================================

def expand_narration(short_text):


    print(
        "Expanding short narration..."
    )


    messages=[

    {
    "role":"system",
    "content":"""

You are a professional motivational speech editor.

Expand the narration naturally.

Rules:

- Keep original meaning
- Make it emotional
- Make it cinematic
- Final length 90-130 words
- No famous quotes

Return only the narration text.

"""
    },

    {
    "role":"user",
    "content":short_text
    }

    ]


    result=cloudflare_request(
        messages,
        max_tokens=800
    )


    return str(result)




# =====================================
# JSON PARSER
# =====================================

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
            "JSON not found"
        )


    return json.loads(
        match.group()
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
        "scenes"
    ]


    for key in required:

        if key not in data:

            print(
                "Missing:",
                key
            )

            return False



    words=len(
        data["narration"].split()
    )


    print(
        "Narration words:",
        words
    )


    # Accept draft because repair exists
    if words < 25:

        print(
            "Narration unusable"
        )

        return False



    if words > 200:

        return False



    if len(data["scenes"]) != 6:

        print(
            "Invalid scenes"
        )

        return False



    for scene in data["scenes"]:


        if "visual" not in scene:

            return False


        for key in [

            "subject",
            "action",
            "emotion",
            "environment",
            "camera"

        ]:

            if not scene["visual"].get(key):

                return False


    return True





# =====================================
# PEXELS
# =====================================

def pexels_search(query):


    key=os.environ["PEXELS_API_KEY"]


    r=requests.get(

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


    r.raise_for_status()


    data=r.json()


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





# =====================================
# MAIN PIPELINE
# =====================================


print(
"Starting Motivational Factory V3"
)


final=None



for attempt in range(5):


    try:


        print(
            "Attempt",
            attempt+1
        )


        raw=cloudflare_generate()


        data=parse_json(raw)



        if validate(data):


            words=len(
                data["narration"].split()
            )


            if words < 90:


                data["narration"]=expand_narration(
                    data["narration"]
                )


                print(
                    "Narration repaired"
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
        "Generation failed"
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

        "visual":scene["visual"],

        "query":scene.get(
            "pexels_query",
            ""
        ),

        "videos":pexels_search(
            scene.get(
                "pexels_query",
                "cinematic motivation"
            )
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
"FACTORY V3 COMPLETE"
)

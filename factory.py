import os
import json
import re
import time
import requests
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



# =====================================
# CLOUDFLARE AI GENERATION
# =====================================

def cloudflare_generate():

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]


    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )


    payload = {

        "messages":[

            {
                "role":"system",

                "content":"""

You are a professional motivational short-form video writer and director.

Create original motivational videos designed for YouTube Shorts,
Instagram Reels and TikTok.

Every video must feel like a mini cinematic story.

Requirements:

- Narration length: 100-180 words
- Duration target: 40-60 seconds
- Strong first 3 second hook
- Emotional progression
- Clear lesson
- Memorable ending
- No famous quotes
- No copied motivational phrases
- Avoid generic advice

Structure:

1. HOOK
Grab attention immediately.

2. STRUGGLE
Show the challenge or internal conflict.

3. REALIZATION
Reveal the important lesson.

4. ACTION
Show what changes.

5. TRANSFORMATION
Show progress.

6. FINAL PAYOFF
End with a powerful memorable message.


For every scene provide:

- What is happening
- Who is involved
- Action
- Emotion
- Environment
- Camera style

Visuals must represent the exact narration moment.

Return ONLY valid JSON.
"""

            },


            {

                "role":"user",

                "content":"""

Create a motivational Short.

Choose a unique topic from:

discipline,
failure,
confidence,
fear,
consistency,
dreams,
success,
self-belief,
hard work,
personal growth.

Do not reuse common examples.

Return:

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

Create exactly 6 scenes.

"""

            }

        ],


        "max_tokens":3500

    }


    response=requests.post(

        url,

        headers={

            "Authorization":f"Bearer {token}",

            "Content-Type":"application/json"

        },

        json=payload,

        timeout=120

    )


    response.raise_for_status()


    data=response.json()


    result=data["result"]


    if isinstance(result,dict):

        if "response" in result:

            return result["response"]


        return result


    return result





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
            "No JSON found"
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

            return False



    narration=data["narration"]


    words=len(
        narration.split()
    )


    if words < 100:

        print(
            "Narration too short:",
            words
        )

        return False



    if words > 180:

        print(
            "Narration too long:",
            words
        )

        return False



    scenes=data["scenes"]


    if len(scenes)!=6:

        return False



    previous=[]


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

                return False



        concept=visual["action"].lower()


        if concept in previous:

            print(
                "Repeated scene"
            )

            return False



        previous.append(
            concept
        )


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

        videos.append(

            {

            "id":video["id"],

            "url":video["url"]

            }

        )


    return videos





# =====================================
# PIPELINE
# =====================================

print(
"Starting Motivational Factory V2"
)


final=None



for attempt in range(3):


    try:


        print(
            "Generation attempt",
            attempt+1
        )


        result=cloudflare_generate()


        data=parse_json(result)



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


    assets.append(

        {

        "scene":scene["scene"],

        "visual":scene["visual"],

        "query":scene["pexels_query"],

        "videos":pexels_search(

            scene["pexels_query"]

        )

        }

    )





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
"FACTORY V2 COMPLETE"
)

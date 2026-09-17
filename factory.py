import os
import json
import re
import time
import requests
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



# ======================================
# CLOUDFLARE AI
# ======================================

def cloudflare_ai(messages, max_tokens=4000):


    account=os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token=os.environ["CLOUDFLARE_API_TOKEN"]


    url=(
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )


    r=requests.post(

        url,

        headers={
            "Authorization":f"Bearer {token}",
            "Content-Type":"application/json"
        },

        json={
            "messages":messages,
            "max_tokens":max_tokens
        },

        timeout=120
    )


    r.raise_for_status()


    result=r.json()["result"]


    if isinstance(result,dict):

        return result.get(
            "response",
            result
        )


    return result





# ======================================
# V5 CINEMATIC DIRECTOR
# ======================================

def generate_director_plan():


    messages=[


{
"role":"system",

"content":"""

You are a world-class motivational short film director,
cinematic editor, SEO strategist and branding expert.

Create a premium motivational YouTube Short production plan.

The style is:

- cinematic
- philosophical
- emotional
- luxury documentary
- inspirational


Avoid:

- random stock footage
- generic quotes
- childish designs
- simple slideshow feeling


The video should feel like a professional motivational channel.


Create:


1. Motivational concept

2. Cinematic visual world

Examples:

- Stoic philosophy
- Ancient warriors
- Modern success
- Nature transformation
- Human resilience


3. Background strategy.

Use Pexels-friendly searches.

Prefer:

- statues
- landscapes
- architecture
- silhouettes
- cinematic environments


4. Narration:

90-130 words.

Structure:

Hook
Problem
Realization
Transformation
Final lesson


5. Caption design:

Create viral short-form captions.

Rules:

- Large centered text
- Word emphasis
- Mobile readable
- Premium typography


6. SEO:

Generate:

- title
- description
- hashtags


Return ONLY JSON.

"""
},


{
"role":"user",

"content":"""

Create one motivational Short.

Return:


{

"title":"",

"theme":"",

"narration":"",


"visual_world":{

"concept":"",
"mood":"",
"style":"",
"color_palette":[]
},


"background_queries":[

""

],


"quote_overlays":[

""

],


"caption_style":{

"font":"",
"animation":"",
"primary_color":"",
"secondary_color":""

},


"seo":{

"title":"",
"description":"",
"hashtags":[]

}


}


"""
}

]


    return cloudflare_ai(messages)





# ======================================
# JSON PARSER
# ======================================

def parse_json(text):


    if isinstance(text,dict):

        return text


    text=str(text)


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





# ======================================
# VALIDATION
# ======================================

def validate(data):


    required=[

        "title",
        "theme",
        "narration",
        "visual_world",
        "background_queries",
        "caption_style",
        "seo"

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
        "Narration words:",
        words
    )


    if words < 50:

        return False


    if len(
        data["background_queries"]
    ) < 3:

        return False


    return True





# ======================================
# PEXELS
# ======================================

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


    output=[]


    for video in data.get(
        "videos",
        []
    ):

        output.append({

            "id":video["id"],

            "url":video["url"]

        })


    return output





# ======================================
# PIPELINE
# ======================================

print(
"Starting Motivational Factory V5"
)



final=None



for attempt in range(5):


    try:


        print(
            "Attempt",
            attempt+1
        )


        raw=generate_director_plan()


        data=parse_json(raw)


        if validate(data):

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
        "V5 generation failed"
    )





# Save production brief


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





# Generate Pexels assets


assets=[]


for query in final["background_queries"]:


    assets.append({

        "query":query,

        "videos":pexels_search(query)

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
"V5 CINEMATIC DIRECTOR COMPLETE"
)

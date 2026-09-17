import os
import json
import re
import time
import requests
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


def cloudflare_generate():

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )

    payload = {
        "messages": [
            {
                "role": "system",
                "content": """
You are a professional motivational Shorts writer.

Create original motivational videos.

Requirements:
- 30-60 seconds
- Strong hook
- Emotional progression
- Story based
- No copied quotes
- Visuals must match narration
- Return JSON only
"""
            },
            {
                "role": "user",
                "content": """
Create a motivational Short about discipline.

Return exactly:

{
"title":"",
"theme":"",
"hook":"",
"narration":"",
"scenes":[
{
"scene":1,
"voice_line":"",
"visual_description":"",
"pexels_query":"",
"caption":""
}
]
}

Create exactly 6 scenes.
"""
            }
        ],
        "max_tokens":2500
    }


    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":"application/json"
        },
        json=payload,
        timeout=120
    )

    r.raise_for_status()

    data = r.json()

    result = data["result"]


    if isinstance(result, dict):

        if "response" in result:
            return result["response"]

        return result


    return result



def parse_json(value):

    if isinstance(value, dict):
        return value


    value = str(value)

    value = value.replace(
        "```json",
        ""
    )

    value = value.replace(
        "```",
        ""
    )


    match = re.search(
        r"\{.*\}",
        value,
        re.DOTALL
    )


    if not match:
        raise Exception(
            "No JSON detected"
        )


    return json.loads(
        match.group()
    )



def validate(data):

    keys = [
        "title",
        "theme",
        "hook",
        "narration",
        "scenes"
    ]


    for k in keys:
        if k not in data:
            return False


    if len(data["scenes"]) != 6:
        return False


    return True



def pexels_search(query):

    key = os.environ["PEXELS_API_KEY"]


    r = requests.get(
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

    data = r.json()


    output=[]


    for item in data.get("videos", []):

        output.append(
            {
                "id":item["id"],
                "url":item["url"]
            }
        )


    return output



print(
    "Starting Motivational Factory"
)


final=None


for attempt in range(3):

    try:

        print(
            "Attempt",
            attempt+1
        )

        response = cloudflare_generate()

        data = parse_json(response)


        if validate(data):

            final=data
            break


        raise Exception(
            "Validation failed"
        )


    except Exception as e:

        print(
            "Error:",
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

    assets.append(
        {
            "scene":scene["scene"],
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
        indent=2
    )


print(
    "FACTORY COMPLETE"
)

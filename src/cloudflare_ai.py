import os
import requests
import json


MODEL = "@cf/meta/llama-3.1-8b-instruct"


def generate_short_plan(topic="discipline"):

    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/{MODEL}"
    )

    system_prompt = """
You are a professional motivational short-form video writer.

Create original motivational Shorts for YouTube Shorts,
Instagram Reels, and TikTok.

Requirements:
- 30-60 seconds narration
- Strong emotional hook in first sentence
- Clear beginning, middle, ending
- No clichés copied from famous speeches
- Story-driven, not just quotes
- Visual scenes must match narration exactly
- Return ONLY valid JSON
"""

    user_prompt = f"""
Create one motivational short video about:

Topic:
{topic}

Return this exact JSON structure:

{{
"title": "",
"theme": "",
"hook": "",
"narration": "",
"duration_seconds": 45,
"scenes": [
    {{
        "scene": 1,
        "time": "0-7 seconds",
        "voice_line": "",
        "visual_description": "",
        "pexels_keywords": "",
        "caption_text": ""
    }}
]
}}

Create 6-8 scenes.
Each scene must represent the actual narration moment.
"""

    payload = {
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]
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

    result = response.json()

    return result


if __name__ == "__main__":
    output = generate_short_plan()
    print(json.dumps(output, indent=2))

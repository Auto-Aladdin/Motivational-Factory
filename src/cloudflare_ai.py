import os
import requests
import json

def generate_short_plan():
    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]

    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"

    prompt = {
        "messages": [
            {
                "role": "system",
                "content": "Create original motivational short video plans. Return JSON only."
            },
            {
                "role": "user",
                "content": "Create a 45 second motivational short about discipline with hook, narration, and 6 visual scene ideas."
            }
        ]
    }

    r = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json=prompt,
        timeout=60
    )
    r.raise_for_status()
    return r.json()

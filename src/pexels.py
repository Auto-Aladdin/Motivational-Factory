import os
import requests

def search_videos(query):
    key = os.environ["PEXELS_API_KEY"]
    r = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": key},
        params={"query": query, "per_page": 5},
        timeout=30
    )
    r.raise_for_status()
    return r.json()

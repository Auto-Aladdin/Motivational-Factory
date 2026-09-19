import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import requests


OUTPUT = Path("output")
SEO_FILE = OUTPUT / "seo_metadata.json"


def _clean_text(value, limit=1200):
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def _unique(values):
    seen = set()
    result = []
    for value in values:
        text = _clean_text(value, 200)
        key = text.lower()
        if not text or key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _tokens(*values):
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this", "your",
        "you", "our", "are", "can", "but", "into", "about", "what",
        "when", "where", "how", "why", "its", "it's", "a", "an", "to",
        "of", "in", "on", "is", "be", "it", "as", "at", "by", "or",
        "was", "were", "will", "their", "they", "them", "then", "than",
    }
    seen = set()
    result = []
    for value in values:
        for token in re.findall(r"[A-Za-z0-9']+", str(value or "").lower()):
            if len(token) < 3 or token in stop_words or token in seen:
                continue
            seen.add(token)
            result.append(token)
    return result


def _content_context(data):
    creative = data.get("creative_direction", {}) or {}
    voice = data.get("voice_direction", {}) or {}
    scenes = []

    for scene in data.get("scenes", []) or []:
        visual = scene.get("visual", {}) or {}
        scenes.append(
            {
                "scene": scene.get("scene"),
                "voice_line": _clean_text(scene.get("voice_line", ""), 500),
                "caption": _clean_text(scene.get("caption", ""), 250),
                "visual": {
                    "type": _clean_text(visual.get("type", ""), 120),
                    "subject": _clean_text(visual.get("subject", ""), 180),
                    "action": _clean_text(visual.get("action", ""), 220),
                    "emotion": _clean_text(visual.get("emotion", ""), 140),
                    "environment": _clean_text(visual.get("environment", ""), 180),
                },
            }
        )

    return {
        "title": _clean_text(data.get("title", "")),
        "theme": _clean_text(data.get("theme", "")),
        "hook": _clean_text(data.get("hook", "")),
        "narration": _clean_text(data.get("narration", ""), 3000),
        "creative_direction": {
            "philosophical_theme": _clean_text(
                creative.get("philosophical_theme", ""), 300
            ),
            "emotional_arc": _clean_text(
                creative.get("emotional_arc", ""), 300
            ),
            "visual_style": _clean_text(
                creative.get("visual_style", ""), 300
            ),
            "color_mood": _clean_text(
                creative.get("color_mood", ""), 200
            ),
            "ending_style": _clean_text(
                creative.get("ending_style", ""), 300
            ),
        },
        "voice_direction": {
            "personality": _clean_text(voice.get("personality", ""), 100),
            "emotion": _clean_text(voice.get("emotion", ""), 160),
            "intensity": _clean_text(voice.get("intensity", ""), 100),
        },
        "background_queries": [
            _clean_text(item, 160)
            for item in data.get("background_queries", []) or []
            if _clean_text(item, 160)
        ][:8],
        "scenes": scenes,
    }


def _parse_json(data):
    if isinstance(data, dict):
        return data

    text = str(data or "").strip()
    text = text.replace("```json", "").replace("```", "").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("SEO model response did not contain JSON")

    clean = re.sub(r"[\x00-\x1f\x7f]", " ", match.group(0))
    clean = re.sub(r",\s*([}\]])", r"\1", clean)
    return json.loads(clean)


def _normalise_list(value, maximum=None):
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    result = _unique(value)
    return result[:maximum] if maximum else result


def _normalise_hashtags(value, maximum=None):
    tags = _normalise_list(value, maximum)
    result = []
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = "#" + re.sub(r"[^A-Za-z0-9_]", "", tag.replace(" ", ""))
        if tag == "#":
            continue
        result.append(tag)
    return _unique(result)[:maximum] if maximum else _unique(result)


def _fallback_metadata(data):
    context = _content_context(data)
    title = context["title"] or "Motivational Short"
    theme = context["theme"] or context["creative_direction"]["philosophical_theme"]
    hook = context["hook"] or context["narration"].split(".")[0]
    narration = context["narration"]
    tokens = _tokens(
        title,
        theme,
        hook,
        context["creative_direction"]["philosophical_theme"],
        context["creative_direction"]["emotional_arc"],
        narration,
        *(scene.get("voice_line", "") for scene in context["scenes"]),
    )

    topic_terms = tokens[:12]
    topic_phrase = theme or (" ".join(topic_terms[:4]) if topic_terms else "personal growth")
    short_description = narration[:380].rsplit(" ", 1)[0] if len(narration) > 380 else narration
    description = (
        f"{short_description}\n\n"
        f"This cinematic short explores {topic_phrase.lower()} through a focused motivational perspective. "
        "Use the story's central idea, emotion, and lesson as the basis for viewer discovery."
    ).strip()

    tags = _normalise_hashtags(topic_terms[:5], 5)
    if not tags:
        tags = ["#motivation", "#mindset", "#personalgrowth"]

    return {
        "schema_version": "1.0",
        "generation_status": "fallback",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_basis": {
            "documented_platform_behavior": True,
            "actual_video_semantics": True,
            "live_trend_research_used": False,
            "note": "Fallback generated from the production brief because the SEO model request failed."
        },
        "content_analysis": {
            "title": title,
            "primary_topic": theme or topic_phrase,
            "secondary_topics": topic_terms[1:6],
            "content_type": "cinematic motivational short",
            "emotional_tone": context["creative_direction"]["emotional_arc"] or "motivational",
            "viewer_intent": "find motivation, perspective, or a mindset shift",
            "target_audience": "viewers interested in motivation, mindset, discipline, resilience, and personal growth",
            "core_message": hook or title,
            "main_characters_or_subjects": [
                scene["visual"]["subject"]
                for scene in context["scenes"]
                if scene["visual"]["subject"]
            ][:8],
            "key_actions": [
                scene["visual"]["action"]
                for scene in context["scenes"]
                if scene["visual"]["action"]
            ][:8],
        },
        "youtube_shorts": {
            "title_suggestions": [
                title,
                f"{title} — The Lesson You Need to Hear",
                f"{title} | A Powerful Mindset Shift",
                f"{title} — What This Really Teaches You",
                f"{title} | Motivation for Difficult Days",
            ],
            "description": description,
            "keywords": topic_terms[:12],
            "search_tags": topic_terms[:15],
            "hashtags": tags,
            "hook_suggestions": _unique([hook, f"The real lesson is simple: {hook}", "Watch the final lesson."])[:3],
            "search_phrases": topic_terms[:8],
            "short_description": description[:500],
            "long_description": description,
            "viewer_retention_text": hook or title,
            "category_topic_suggestions": ["People & Blogs", "Education"],
        },
        "tiktok": {
            "caption_options": [
                hook or title,
                f"{hook or title} — this is the mindset shift.",
                f"A reminder about {topic_phrase.lower()} that hits differently.",
            ],
            "keywords": topic_terms[:10],
            "hashtags": tags,
            "hook_suggestions": _unique([hook, "This changes how you see the problem.", "Stay for the final line."])[:3],
            "discovery_phrases": topic_terms[:8],
        },
        "instagram_reels": {
            "caption": description,
            "hashtags": tags[:5],
            "search_keywords": topic_terms[:10],
            "engagement_text": "What part of this message resonates with you most?",
            "discovery_phrases": topic_terms[:8],
        },
        "facebook_reels": {
            "title_caption": title,
            "description": description,
            "keywords": topic_terms[:10],
            "hashtags": tags[:5],
        },
    }


def _normalise_metadata(metadata, data):
    fallback = _fallback_metadata(data)
    if not isinstance(metadata, dict):
        return fallback

    result = fallback
    result["generation_status"] = "ai"

    if metadata.get("content_analysis"):
        result["content_analysis"].update(metadata["content_analysis"])

    platform_specs = {
        "youtube_shorts": {
            "title_suggestions": 8,
            "keywords": 15,
            "search_tags": 20,
            "hashtags": 5,
            "hook_suggestions": 5,
            "search_phrases": 10,
            "category_topic_suggestions": 5,
        },
        "tiktok": {
            "caption_options": 5,
            "keywords": 12,
            "hashtags": 8,
            "hook_suggestions": 5,
            "discovery_phrases": 10,
        },
        "instagram_reels": {
            "hashtags": 5,
            "search_keywords": 12,
            "discovery_phrases": 10,
        },
        "facebook_reels": {
            "keywords": 12,
            "hashtags": 5,
        },
    }

    for platform, fields in platform_specs.items():
        if not isinstance(metadata.get(platform), dict):
            continue
        for field, maximum in fields.items():
            value = metadata[platform].get(field)
            if field == "hashtags":
                normalised = _normalise_hashtags(value, maximum)
            else:
                normalised = _normalise_list(value, maximum)
            if normalised:
                result[platform][field] = normalised

        for scalar in (
            "description",
            "short_description",
            "long_description",
            "caption",
            "engagement_text",
            "title_caption",
            "viewer_retention_text",
        ):
            if scalar in metadata[platform] and metadata[platform][scalar]:
                result[platform][scalar] = _clean_text(metadata[platform][scalar], 5000)

    for platform in ("youtube_shorts", "tiktok", "instagram_reels", "facebook_reels"):
        result[platform]["optimization_note"] = _clean_text(
            metadata.get(platform, {}).get("optimization_note", result[platform].get("optimization_note", "")),
            600,
        )

    result["schema_version"] = "1.0"
    result["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    result["research_basis"] = {
        "documented_platform_behavior": True,
        "actual_video_semantics": True,
        "live_trend_research_used": False,
        "note": "No live trend API is configured; optimization uses current documented platform guidance plus the generated video's actual semantics."
    }
    return result


def generate_seo_metadata(data, output_path=SEO_FILE):
    """Generate one platform-separated SEO JSON artifact from the accepted brief."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
        token = os.environ["CLOUDFLARE_API_TOKEN"]
    except KeyError as exc:
        print(
            "WARNING: SEO model credentials unavailable; using content-derived fallback:",
            exc.args[0],
        )
        metadata = _fallback_metadata(data)
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(metadata, file, indent=2, ensure_ascii=False)
        print("SEO metadata saved:", output_path)
        return metadata

    context = _content_context(data)

    system_prompt = """
You are a senior social-video SEO strategist and metadata editor.

Your job is to create accurate, platform-specific metadata for ONE already-generated short video.
The metadata must represent the actual video, not a generic motivational niche.

RESEARCH PRINCIPLES:
- Use current documented platform behavior as the optimization basis.
- Base every keyword, phrase, title, caption, hook, and hashtag on the actual supplied content.
- Match real viewer search intent and natural language.
- Do not invent people, events, claims, topics, emotions, or actions not supported by the content.
- Do not use unrelated trending terms merely because they are popular.
- Never keyword-stuff.
- Never use misleading clickbait that promises something absent from the video.
- A strong hook may create curiosity, but it must remain truthful to the story.
- No live trend data is available in this request. Do not claim that any keyword is currently trending.

YOUTUBE SHORTS:
- Prioritize clear, compelling titles and accurate descriptions.
- Put the most important topic language naturally near the beginning of the description.
- Provide useful search tags, but do not treat tags as the primary discovery mechanism.
- Provide a small set of highly relevant hashtags, not a large block.
- Give several title and hook alternatives suitable for testing.
- Provide a concise short description, a fuller long description, and a truthful retention-focused opening text.

TIKTOK:
- Align captions, hooks, hashtags, and discovery phrases closely with searchable topic language.
- Prefer concise natural-language search phrases and relevant hashtags.
- Avoid generic viral bait.

INSTAGRAM REELS:
- Favor a readable caption, highly relevant search keywords, and a small targeted hashtag set.
- Do not use hashtag stuffing.
- Include a natural engagement prompt when it fits the content.

FACEBOOK REELS:
- Favor clear titles/captions, concise descriptions, relevant keywords, and a restrained hashtag set.
- Do not use unrelated or excessive metadata.

CONTENT ANALYSIS:
Identify the primary topic, secondary topics, emotional tone, viewer intent, target audience, core message, main subjects/characters, and key actions from the supplied production brief.

RETURN ONLY VALID JSON matching this exact high-level shape:
{
  "content_analysis": {
    "primary_topic": "",
    "secondary_topics": [],
    "content_type": "",
    "emotional_tone": "",
    "viewer_intent": "",
    "target_audience": "",
    "core_message": "",
    "main_characters_or_subjects": [],
    "key_actions": []
  },
  "youtube_shorts": {
    "title_suggestions": [],
    "description": "",
    "short_description": "",
    "long_description": "",
    "keywords": [],
    "search_tags": [],
    "hashtags": [],
    "hook_suggestions": [],
    "viewer_retention_text": "",
    "search_phrases": [],
    "category_topic_suggestions": [],
    "optimization_note": ""
  },
  "tiktok": {
    "caption_options": [],
    "keywords": [],
    "hashtags": [],
    "hook_suggestions": [],
    "discovery_phrases": [],
    "optimization_note": ""
  },
  "instagram_reels": {
    "caption": "",
    "hashtags": [],
    "search_keywords": [],
    "engagement_text": "",
    "optimization_note": ""
  },
  "facebook_reels": {
    "title_caption": "",
    "description": "",
    "keywords": [],
    "hashtags": [],
    "optimization_note": ""
  }
}

QUALITY RULES:
- YouTube title suggestions: 5-8 distinct options; clear topic first, curiosity second.
- YouTube search tags: 8-20 precise terms/phrases.
- YouTube hashtags: 3-5 highly relevant hashtags.
- TikTok caption options: 3-5 options.
- TikTok hashtags: 4-8 relevant hashtags.
- Instagram hashtags: no more than 5 targeted hashtags.
- Facebook hashtags: 2-5 targeted hashtags.
- Avoid repeated variants that say essentially the same thing.
- Search phrases should look like things a real viewer might type.
- Category/topic suggestions should be relevant to the actual content, not just "motivation" by default.
""".strip()

    user_prompt = (
        "Create SEO metadata for this exact generated short.\n\n"
        "PRODUCTION BRIEF:\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/llama-3.1-8b-instruct"
    )

    try:
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 3500,
            },
            timeout=120,
        )
        response.raise_for_status()

        result = response.json().get("result")
        if isinstance(result, dict):
            result = result.get("response", result)

        metadata = _normalise_metadata(_parse_json(result), data)

    except Exception as seo_error:
        print(
            "WARNING: SEO model generation failed; using content-derived fallback:",
            seo_error,
        )
        metadata = _fallback_metadata(data)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)

    print("SEO metadata saved:", output_path)
    return metadata

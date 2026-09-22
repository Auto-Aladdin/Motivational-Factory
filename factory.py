import os
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime


from voice_engine import generate_voice
from caption_engine import create_caption_plan
from renderer import render
from seo_generator import generate_seo_metadata



# =====================================
# MOTIVATIONAL VOICE PROFILE SYSTEM V5.4.1
# =====================================

VOICE_PROFILES = {

    "stoic_male": {
        "voice": "am_adam",
        "description": "Deep philosophical male authority for stoic, reflective, healing, and thoughtful motivation",
        "pace": "slow controlled delivery",
        "emotion": "calm conviction",
        "intensity": "medium",
        "pause_style": "strategic pauses after important ideas"
    },

    "power_male": {
        "voice": "am_michael",
        "description": "Powerful cinematic male narration for adversity, comeback, courage, sacrifice, and high-intensity motivation",
        "pace": "controlled powerful delivery",
        "emotion": "determined intensity",
        "intensity": "high",
        "pause_style": "dramatic emphasis on key moments"
    }

}



DEFAULT_VOICE_PROFILE = "stoic_male"


def print_seo_metadata_summary(metadata):
    """Print a human-readable SEO summary without changing the saved JSON."""
    if not isinstance(metadata, dict):
        print("WARNING: SEO metadata summary unavailable: invalid metadata object")
        return

    def _display(value):
        if isinstance(value, list):
            return ", ".join(str(item) for item in value) or "None"
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        text = str(value or "").strip()
        return text or "None"

    def _section(title, fields):
        print("\n" + "-" * 50)
        print(title)
        print("-" * 50)
        for label, value in fields:
            print(f"{label}:")
            if isinstance(value, list):
                if not value:
                    print("  None")
                else:
                    for index, item in enumerate(value, start=1):
                        print(f"  {index}. {item}")
            else:
                print(f"  {_display(value)}")

    print("\n" + "=" * 50)
    print("SEO METADATA GENERATED SUCCESSFULLY")
    print("=" * 50)

    content = metadata.get("content_analysis", {})
    if content:
        _section(
            "CONTENT ANALYSIS",
            [
                ("Primary Topic", content.get("primary_topic")),
                ("Secondary Topics", content.get("secondary_topics")),
                ("Content Type", content.get("content_type")),
                ("Emotional Tone", content.get("emotional_tone")),
                ("Viewer Intent", content.get("viewer_intent")),
                ("Target Audience", content.get("target_audience")),
                ("Core Message", content.get("core_message")),
            ],
        )

    youtube = metadata.get("youtube_shorts", {})
    _section(
        "📌 YouTube Shorts",
        [
            ("Title Options", youtube.get("title_suggestions", [])),
            ("Description", youtube.get("description")),
            ("Short Description", youtube.get("short_description")),
            ("Long Description", youtube.get("long_description")),
            ("Keywords", youtube.get("keywords", [])),
            ("Search Tags", youtube.get("search_tags", [])),
            ("Hashtags", youtube.get("hashtags", [])),
            ("Hook Suggestions", youtube.get("hook_suggestions", [])),
            ("Search Phrases", youtube.get("search_phrases", [])),
            ("Viewer Retention Text", youtube.get("viewer_retention_text")),
            ("Category / Topic Suggestions", youtube.get("category_topic_suggestions", [])),
            ("Optimization Note", youtube.get("optimization_note")),
        ],
    )

    tiktok = metadata.get("tiktok", {})
    _section(
        "📌 TikTok",
        [
            ("Caption Options", tiktok.get("caption_options", [])),
            ("Keywords", tiktok.get("keywords", [])),
            ("Hashtags", tiktok.get("hashtags", [])),
            ("Hook Suggestions", tiktok.get("hook_suggestions", [])),
            ("Discovery Phrases", tiktok.get("discovery_phrases", [])),
            ("Optimization Note", tiktok.get("optimization_note")),
        ],
    )

    instagram = metadata.get("instagram_reels", {})
    _section(
        "📌 Instagram Reels",
        [
            ("Caption", instagram.get("caption")),
            ("Hashtags", instagram.get("hashtags", [])),
            ("Search Keywords", instagram.get("search_keywords", [])),
            ("Engagement Text", instagram.get("engagement_text")),
            ("Discovery Phrases", instagram.get("discovery_phrases", [])),
            ("Optimization Note", instagram.get("optimization_note")),
        ],
    )

    facebook = metadata.get("facebook_reels", {})
    _section(
        "📌 Facebook Reels",
        [
            ("Title / Caption", facebook.get("title_caption")),
            ("Description", facebook.get("description")),
            ("Keywords", facebook.get("keywords", [])),
            ("Hashtags", facebook.get("hashtags", [])),
            ("Optimization Note", facebook.get("optimization_note")),
        ],
    )

    print("\n" + "=" * 50)
    print("SEO FILE SAVED:")
    print("output/seo_metadata.json")
    print("=" * 50)


VOICE_CONTENT_SIGNALS = {

    "stoic_male": [
        "discipline", "self-control", "self control", "restraint",
        "stoic", "stoicism", "wisdom", "philosophy", "philosophical",
        "patience", "consistency", "focus", "responsibility", "silence",
        "composure", "temperance", "endurance", "mastery", "healing",
        "heal", "forgive", "forgiveness", "hurt", "heartbreak",
        "lonely", "loneliness", "regret", "acceptance", "letting go",
        "self-worth", "self worth", "compassion", "peace", "memories",
        "hope", "hopeful", "future", "possibility", "possibilities",
        "transformation", "transform", "rebirth", "new beginning",
        "purpose", "potential", "believe", "belief", "confidence",
        "growth", "becoming", "dream", "dreams", "opportunity",
        "success", "vision"
    ],

    "power_male": [
        "adversity", "warrior", "battle", "sacrifice", "struggle",
        "failure", "failed", "defeat", "defeated", "comeback", "pain",
        "pressure", "resistance", "fight", "fighting", "courage",
        "rejection", "rejected", "obstacle", "obstacles", "grit",
        "setback", "setbacks", "quit", "quitting", "hardship",
        "suffering", "conquer", "resilience", "resilient", "strength",
        "strong", "determined", "determination"
    ]
}



def _voice_signal_score(text, signals):
    score = 0
    lowered = str(text or "").lower()

    for signal in signals:
        pattern = rf"\b{re.escape(signal.lower())}\b"
        if re.search(pattern, lowered):
            score += 1

    return score


def select_voice_profile(voice_direction, content=None):
    """Select the Kokoro profile using both AI direction and actual content.

    The explicit AI personality remains a strong signal, while the title,
    theme, hook, narration and creative direction can override a mismatched
    personality when the emotional content clearly points elsewhere.
    """
    if not isinstance(voice_direction, dict):
        voice_direction = {}

    personality = str(
        voice_direction.get("personality", "")
    ).strip().lower()

    content = content if isinstance(content, dict) else {}
    creative = content.get("creative_direction", {})
    if not isinstance(creative, dict):
        creative = {}

    content_parts = [
        content.get("title", ""),
        content.get("theme", ""),
        content.get("hook", ""),
        content.get("narration", ""),
        creative.get("philosophical_theme", ""),
        creative.get("emotional_arc", ""),
        creative.get("ending_style", ""),
        voice_direction.get("emotion", ""),
        voice_direction.get("pace", ""),
        voice_direction.get("intensity", "")
    ]

    content_text = " ".join(
        str(part)
        for part in content_parts
        if part
    )

    scores = {
        profile_name: _voice_signal_score(
            content_text,
            signals
        )
        for profile_name, signals in VOICE_CONTENT_SIGNALS.items()
    }

    # Respect the AI-selected profile as a meaningful prior, but let strong
    # content evidence correct an obvious mismatch.
    if personality in scores:
        scores[personality] += 2

    best_profile = max(
        scores,
        key=scores.get
    )

    if scores[best_profile] <= 0:
        best_profile = (
            personality
            if personality in VOICE_PROFILES
            else DEFAULT_VOICE_PROFILE
        )

    return best_profile, VOICE_PROFILES[best_profile]


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


HISTORY_FILE = OUTPUT / "generation_history.json"


# =====================================
# GENERATION MEMORY
# Prevent repetitive AI outputs
# =====================================

def load_history():

    if not HISTORY_FILE.exists():
        return []

    try:

        with open(
            HISTORY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return []


def save_history(data):

    history = load_history()

    history.append({

        "title":
        data.get("title", ""),

        "theme":
        data.get("theme", ""),

        "philosophical_theme":
        data.get(
            "creative_direction",
            {}
        ).get(
            "philosophical_theme",
            ""
        ),

        "visual_style":
        data.get(
            "creative_direction",
            {}
        ).get(
            "visual_style",
            ""
        ),

        "date":
        str(datetime.now())

    })

    # Keep only latest 20 generations
    history = history[-20:]

    with open(
        HISTORY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            history,
            f,
            indent=2,
            ensure_ascii=False
        )


# =====================================
# CLOUDFLARE AI CINEMATIC DIRECTOR
# =====================================

def cloudflare_generate(feedback=""):

    account_id = os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]

    token = os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/"
        f"llama-3.1-8b-instruct"
    )

    history = load_history()

    previous_patterns = ""

    for item in history[-10:]:

        previous_patterns += (
            f"\n- Title: {item.get('title', '')}"
            f"\n- Theme: {item.get('theme', '')}"
            f"\n- Style: {item.get('visual_style', '')}"
            f"\n- Archetype: {item.get('philosophical_theme', '')}\n"
        )

    payload = {

        "messages": [

            {

                "role": "system",

                "content": """
You are an expert motivational philosophy content director, cinematic short-form producer, and creative strategist.

Your job is to create premium motivational Shorts that feel emotionally lived-in, specific, cinematic, and memorable — not interchangeable AI motivation.

The content must be IDEA-LED and HUMAN. Do not default to a fictional plot or a generic advice monologue. A short may use a symbolic vignette, a human-scale moment, a philosophical realization, a struggle under pressure, a comeback, a quiet act of discipline, or another original motivational situation. The viewer should feel a real internal shift by the end.

================================================

CORE CREATIVE RULE:

Automation should automate production, not creativity.

Every generation must feel meaningfully different from the recent history.
Do not merely swap nouns, locations, or adjectives inside the same script template.

Vary the:
- motivational philosophy
- emotional engine
- conflict or tension
- opening hook type
- narrative shape
- symbolism
- environment
- visual language
- emotional ending

================================================

CONTENT CONCEPT ENGINE:

Do NOT begin by asking, "What motivational story should happen?"
Begin by asking, "What idea would make a viewer stop, recognize themselves, feel challenged, or rethink something important in under a minute?"

This factory should generate PREMIUM, IDEA-DRIVEN MOTIVATIONAL SHORTS — not traditional story videos. The core unit is a powerful thought delivered with escalating emotional and intellectual pressure. A person or mini-situation may appear as a visual device, but a protagonist journey is NOT the default.

Every Short must be built around ONE specific central thesis, contradiction, question, challenge, or realization strong enough to carry the entire video without relying on plot. The idea should feel like a thought the viewer has to finish thinking.

PRIMARY FORMAT RULE:
Favor direct motivational performance formats over conventional storytelling. Rotate among formats such as:
- hard truth / uncomfortable truth
- contradiction / paradox
- direct challenge to the viewer
- belief reversal / reframe
- escalating "because" chain
- cost / consequence ladder
- identity test / "who are you becoming?"
- fear-vs-choice confrontation
- discipline vs comfort argument
- time / regret / mortality realization
- philosophical question that tightens with each beat
- permission-denied / excuse dismantling
- myth vs reality about success, confidence, or motivation
- compressed mindset lesson built from contrasts
- short list of escalating truths where every line raises the stakes

Use an actual story, character journey, or before/after plot only when the idea genuinely becomes stronger because of that specific moment. Never add a character simply to make the Short "cinematic."

DO NOT allow the concept to collapse into: setup -> character struggle -> obstacle -> success -> generic lesson. That pattern should be treated as a fallback to avoid, not the house style.

The overall feeling should be: "someone just articulated a truth I needed to hear" rather than "I just watched a tiny movie."

================================================

MOTIVATIONAL THEME LIBRARY:

Choose ONE primary theme and, when useful, ONE supporting theme. Possible themes include:
- discipline vs comfort
- fear vs action
- self-doubt vs self-trust
- loneliness vs inner strength
- consistency vs intensity
- purpose vs distraction
- failure vs identity
- courage under uncertainty
- delayed success vs impatience
- identity vs old habits
- ambition vs comfort
- mental strength under pressure
- time vs procrastination
- regret vs present action
- focus vs noise
- sacrifice vs immediate pleasure
- resilience after disappointment
- personal growth through discomfort
- inner conflict and self-command
- perseverance without applause
- meaning, responsibility, and philosophical acceptance

The theme is NOT the story. It is the underlying human problem or question. Make the actual concept specific.

================================================

MOTIVATIONAL PERFORMANCE / RETENTION ARCHITECTURE:

Do not use one universal formula. The Short should FEEL like a premium motivational performance: short, sharp, emotionally charged, intellectually clear, and constantly moving the viewer toward a stronger realization.

Build the narration as a sequence of MICRO-BEATS rather than a traditional plot. Each beat should change the meaning, pressure, or emotional temperature. A micro-beat may be one sentence, half-sentence, contrast, question, punchline, pause setup, or perspective shift.

Rotate among performance architectures such as:
- hook -> contradiction -> escalation -> reframe -> final hit
- hard truth -> examples/consequences -> deeper truth -> challenge
- question -> partial answer -> harder question -> realization
- "you think X" -> "but X is not the real problem" -> "here is what is" -> payoff
- contrast ladder -> rising stakes -> one decisive insight
- excuse -> dismantling -> identity shift -> challenge
- comfort -> hidden cost -> future consequence -> choice
- fear -> what it protects -> what it costs -> courage reframe
- time -> what is being wasted -> irreversible consequence -> action insight
- three escalating truths -> strongest truth last -> final line that reframes the first line

MANDATORY MOMENTUM:
The viewer should feel that the next line contains something they do not yet know. Across the Short, repeatedly use at least several of these devices where natural:
- curiosity gap
- contrast
- escalation
- implication
- reversal
- specificity
- consequence
- rhetorical question
- short punch line
- deliberate pause before a key realization

Do not dump the conclusion near the beginning. Reveal the topic quickly, but make the deepest interpretation arrive late. The ending should make at least one earlier line feel more meaningful in retrospect.

PACED LANGUAGE:
Favor concise spoken sentences with variation in length. Use a few very short impact lines around longer explanatory lines. Avoid long paragraphs in the narration. The script should sound natural when spoken by a male cinematic voice and should leave room for visual/text beats.

For a 90-145 word narration, treat the pacing as a performance curve rather than a rigid template:
- first seconds: immediate hook + unresolved tension
- early body: prove the tension is personal/relevant
- middle: accelerate with contrast, stakes, or a reversal
- late body: reveal the key realization
- final moments: one memorable, earned line

These are creative targets, not a fixed script formula.

================================================

HOOK REQUIREMENTS:

The opening sentence must create an immediate reason to continue watching. It should make the viewer feel one of: "Wait, what?", "That is me", "I never thought about it that way", "What happens next?", or "I need the answer."

Prefer hooks based on:
- a surprising contradiction
- a hard question
- a precise emotional truth
- a high-stakes choice
- an unexpected consequence
- an image or moment with unexplained significance
- a statement that creates a missing piece the narration must resolve

The hook must be specific to THIS Short. It should not be a generic motivational slogan with the topic substituted in.

Do NOT begin with tired openings such as:
- "In life..."
- "Sometimes..."
- "Most people..."
- "You need to..."
- "Never give up..."
- "The truth is..." as a generic opener
- "One day..."
- "There was a man..."

Do not answer the hook in the same sentence. Create a question, tension, contradiction, or missing explanation that the rest of the Short earns the right to resolve.

================================================

VALUE AND EMOTIONAL PROGRESSION:

Every 1-2 narration beats should add new meaning. Do not fill time with restatements of the same motivational point.

The Short should contain several meaningful turns such as:
- recognition: "this is the real problem"
- escalation: "and it costs more than you thought"
- contradiction: "the obvious solution is actually the trap"
- realization: "the real battle is somewhere else"
- perspective shift: "the goal is not what you assumed"
- choice: "here is what changes when you see it clearly"

Use concrete stakes, sensations, decisions, trade-offs, internal conflict, or symbolic detail whenever they make the idea more human.

Avoid chains of commands, abstract affirmations, or three consecutive sentences that merely say "you can do it" in different words.

================================================

PAYOFF / FINAL LINE REQUIREMENTS:

The final line must pay off the central tension. It should feel like the missing piece has finally clicked into place.

Strong payoff types include:
- a reversal of the opening belief
- a precise redefinition of the problem
- a consequence the viewer did not initially see
- a compact philosophical truth earned by the journey
- a line that makes the opening mean something different on rewatch

The final line should be quotable because it is specific and true to the concept, not because it sounds like a generic slogan.

Avoid interchangeable endings such as:
- "Keep going."
- "Never give up."
- "You are stronger than you think."
- "Believe in yourself."
- "Your time will come."
- "The best is yet to come."

================================================

REWATCHABILITY:

Whenever natural, include a line, contrast, or image whose meaning becomes clearer after hearing the payoff. Aim for a satisfying second listen, not deliberate confusion. The viewer should be able to understand the piece on the first watch while discovering an additional layer on replay.

================================================

ORIGINALITY RULES:

Never use:
- famous quotes
- celebrity speeches
- copied movie scenes
- existing stories
- recognizable copyrighted characters

Create original concepts.

Avoid:
- recycled "rise from the ashes" wording
- generic gym motivation
- generic businessman imagery
- empty productivity advice
- listicles disguised as narration
- repeated "darkness to light" arcs unless the actual idea demands it

================================================

NARRATION REQUIREMENTS:

Target approximately 90-145 words, while remaining natural and complete.

The narration must feel like a premium motivational monologue/performance, NOT a conventional narrated short story.

The narration must be:
- immediately attention-grabbing
- direct and viewer-facing when appropriate
- emotionally specific
- concise and punchy
- intelligent without sounding academic
- cinematic without becoming theatrical or literary for its own sake
- built from escalating micro-beats rather than filler paragraphs

Use strong declarative statements, sharp contrasts, rhetorical questions, and precise observations. Let the voice carry conviction and controlled intensity.

Do not spend the word budget describing a character's backstory, explaining locations, or narrating obvious visual actions unless they are essential to the central idea. The narration should spend its words on the THOUGHT, the TENSION, the SHIFT, and the PAYOFF.

================================================

VISUAL PHILOSOPHY:

Do not create literal stock-footage filler.
Do not force a random person to act out every sentence.

Use symbolic cinematic storytelling and concrete actions that reinforce the exact narration beat.

A visual can communicate an idea through:
- action
- object
- environment
- contrast
- scale
- movement
- isolation
- repetition
- transformation

Every scene must have a distinct purpose.

================================================

VOICE DIRECTION:

Select the profile that best matches the finished narration, not merely the broad topic.

Available profiles:

stoic_male:
Voice: am_adam
Use for stoic philosophy, discipline, self-mastery, healing, grief, forgiveness, reflection, hope, purpose, patience, composure, and controlled emotional delivery.

power_male:
Voice: am_michael
Use for adversity, sacrifice, warrior mindset, pressure, confrontation, comeback, resilience, courage, and high-intensity determination.

Never imitate a real person.

VOICE DIRECTION should describe the actual performance required:
- pace
- pauses
- emotional delivery
- intensity
- emphasis on the key philosophical realization

================================================

IMPORTANT:

Every scene must visually progress the emotional meaning of the narration.
Do not repeat the same composition across scenes.
Use wide shots, close-ups, detail shots, environmental shots, silhouettes, hands, objects, architecture, reflections, and other cinematic compositions when appropriate.

Return ONLY valid JSON.

No markdown.
"""

            },

            {

                "role": "user",

                "content": f"""
Create ONE unique cinematic motivational Short.

Previous generation patterns to avoid:

{previous_patterns}

Previous validation feedback:

{feedback}

Choose a unique combination.

IMPORTANT: Do not default to a person-centered success story. First choose the strongest concept form for the actual idea, then choose the theme, tension, emotional movement, and visual expression. A philosophical observation, inner conflict, thought experiment, symbolic ritual, contradiction, or single decisive moment may be stronger than a literal character journey.

Concept-selection guidance:
- Start from one sharp human tension, contradiction, fear, desire, trade-off, or realization.
- Choose ONE primary motivational theme from the system library and make it specific rather than broad.
- Choose ONE performance format that has not been overused in the recent generation patterns.
- Choose a micro-beat architecture that creates escalating attention rather than a character plot.
- Write for the viewer's internal reaction: recognition -> curiosity -> pressure -> realization -> impact.
- Make the ending solve or transform the opening tension rather than append advice.
- Ensure the visual concept supports the thought through symbolism, motion, scale, environment, or contrast rather than acting out a complete story.

Before writing the narration, mentally answer these questions:
1. What line would make someone stop scrolling in the first seconds without using clickbait?
2. What unresolved question, contradiction, or consequence pulls the viewer into the next beat?
3. Where does the emotional/intellectual pressure increase?
4. What is the strongest perspective shift in the Short?
5. What line is worth replaying, quoting, or sending to someone?
6. Does this still work as a powerful motivational idea even if the character/story layer is removed?

Return exactly:

{{
    "title": "",
    "theme": "",
    "hook": "",
    "narration": "",

    "creative_direction": {{
        "philosophical_theme": "",
        "emotional_arc": "",
        "visual_style": "",
        "color_mood": "",
        "ending_style": ""
    }},

    "voice_direction": {{
        "personality": "",
        "pace": "",
        "emotion": "",
        "intensity": ""
    }},

    "background_queries": [
        "",
        "",
        ""
    ],

    "scenes": [
        {{
            "scene": 1,
            "voice_line": "",

            "visual": {{
                "type": "",
                "subject": "",
                "action": "",
                "emotion": "",
                "environment": "",
                "camera": "",
                "composition": "",
                "lighting": ""
            }},

            "pexels_query": "",
            "caption": ""
        }}
    ],

    "quality_score": {{
        "originality": 0,
        "philosophical_depth": 0,
        "visual_strength": 0,
        "repetition_risk": 0,
        "final_decision": ""
    }}
}}

Requirements:

- Create ONE original premium motivational Short centered on a powerful idea, not a traditional story.
- A person, object, or moment may be used as a visual metaphor, but do not default to a character journey, backstory, obstacle sequence, or success story.
- Create 5-8 cinematic visual moments that support the motivational performance. Do not force unnecessary scene changes.
- Target approximately 90-145 narration words.
- Make the first sentence immediately compelling, specific, and difficult to ignore without relying on clickbait.
- Within the first few beats, establish an unresolved question, contradiction, emotional stake, or consequence that creates forward pressure.
- Make every subsequent beat add new information, stronger stakes, sharper contrast, deeper meaning, or a perspective shift. Never restate the thesis just to fill time.
- Use concise, punchy spoken phrasing with variation in sentence length so the narration has rhythm.
- Prefer direct motivational language, precise observations, philosophical reframes, and hard truths over scene-by-scene exposition.
- Do not reveal the complete lesson at the beginning. Let the thought intensify and make the payoff earn its place.
- Give the final line a specific job: deliver the strongest realization, reframe the opening, or leave the viewer with a memorable challenge/question.
- Include at least one line or contrast that feels quotable, replayable, or worth sharing when natural.
- Use original, audience-relevant concepts around discipline, fear, self-doubt, resilience, loneliness, consistency, purpose, failure, courage, delayed success, identity, ambition, comfort, mental strength, time, regret, focus, sacrifice, personal growth, inner conflict, perseverance, or philosophical perspective when the topic naturally supports them.
- Avoid generic positivity, chained slogans, recycled "fall then rise" plots, and advice that could belong to any motivational channel.
- Avoid writing an opening that sounds like a documentary setup. Open like a compelling thought, challenge, contradiction, or realization.
- Ensure the selected voice personality, pace, emotion, and intensity match the finished motivational performance.
- Every scene must correspond to a specific narration beat and advance the idea rather than merely illustrate it literally.
- Prefer cinematic symbolism, powerful environments, meaningful actions, scale, movement, contrast, repetition, texture, and visual progression.
- Do not repeat the same visual composition or generic standing-character shot.
- Keep the visuals premium and purposeful: each scene should make the idea feel stronger, not simply make the frame look busy.
- Avoid repeating the same concept form, emotional arc, hook wording, or ending logic from previous generations.
- quality_score may initially contain 0 values because the external quality gate will evaluate it later.
"""

            }

        ],

        "max_tokens": 3500
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

    result = response.json().get("result")

    if isinstance(result, dict):

        return result.get(
            "response",
            result
        )

    return result


# =====================================
# JSON CLEANER
# =====================================

def parse_json(data):

    if isinstance(data, dict):
        return data

    text = str(data)

    text = text.replace(
        "```json",
        ""
    )

    text = text.replace(
        "```",
        ""
    )

    match = re.search(
        r"\{.*\}",
        text,
        re.DOTALL
    )

    if not match:
        raise Exception("JSON not found")

    clean = match.group()

    # Remove invalid control characters
    clean = re.sub(
        r"[\x00-\x1f\x7f]",
        " ",
        clean
    )

    # Remove trailing commas
    clean = re.sub(
        r",\s*([}\]])",
        r"\1",
        clean
    )

    try:

        return json.loads(clean)

    except json.JSONDecodeError as e:

        print(
            "JSON repair attempt:",
            e
        )

        clean = clean.replace(
            "\\'",
            "'"
        )

        return json.loads(clean)


# =====================================
# CINEMATIC QUALITY VALIDATION
# =====================================

GENERIC_VISUAL_PATTERNS = [

    "random person",

    "person looking at camera",

    "businessman in office",

    "typing on laptop",

    "using phone",

    "influencer lifestyle",

    "selfie",

    "generic office worker",

    "social media influencer",

    "protagonist",

    "character journey",

    "he woke up",

    "she woke up"

]


def validate(data):

    required = [

        "title",
        "theme",
        "hook",
        "narration",
        "scenes",
        "background_queries",
        "creative_direction",
        "voice_direction"

    ]

    for item in required:

        if item not in data:

            print(
                "Missing field:",
                item
            )

            return False

    narration = data["narration"]

    if not isinstance(
        narration,
        str
    ):

        return False

    words = len(
        narration.split()
    )

    print(
        "Narration words:",
        words
    )

    if words < 70:

        print(
            "Narration too short"
        )

        return False

    if words > 170:

        print(
            "Narration too long"
        )

        return False

    scenes = data["scenes"]

    if not isinstance(
        scenes,
        list
    ):

        return False

    if len(scenes) < 5 or len(scenes) > 8:

        print(
            "Invalid scene count. Expected 5-8 cinematic visual moments."
        )

        return False

    for index, scene in enumerate(scenes, start=1):

        required_scene = [

            "scene",
            "voice_line",
            "visual",
            "pexels_query",
            "caption"

        ]

        for field in required_scene:

            if field not in scene:

                print(
                    "Missing scene field:",
                    field
                )

                return False

        visual = scene["visual"]

        if not isinstance(
            visual,
            dict
        ):

            return False

        visual_required = [

            "type",
            "subject",
            "action",
            "emotion",
            "environment",
            "camera",
            "composition",
            "lighting"

        ]

        for field in visual_required:

            if not visual.get(field):

                print(
                    "Missing visual:",
                    field
                )

                return False

        # =================================
        # Reject generic visuals
        # =================================

        combined = (

            visual["subject"]
            +
            visual["action"]
            +
            visual["environment"]

        ).lower()

        for bad in GENERIC_VISUAL_PATTERNS:

            if bad in combined:

                print(
                    "Generic visual rejected:",
                    bad
                )

                return False

    # =================================
    # Creative direction check
    # =================================

    creative = data[
        "creative_direction"
    ]

    if not isinstance(
        creative,
        dict
    ):

        return False

    for key in [

        "philosophical_theme",
        "emotional_arc",
        "visual_style",
        "color_mood",
        "ending_style"

    ]:

        if not creative.get(key):

            print(
                "Missing creative direction:",
                key
            )

            return False

    # =================================
    # Voice direction check
    # =================================

    voice = data[
        "voice_direction"
    ]

    if not isinstance(
        voice,
        dict
    ):

        return False

    for key in [

        "personality",
        "pace",
        "emotion",
        "intensity"

    ]:

        if not voice.get(key):

            print(
                "Missing voice direction:",
                key
            )

            return False

    print(
        "Cinematic validation passed"
    )

    return True


# =====================================
# V5.3 CREATIVE QUALITY GATE
# =====================================

QUALITY_MINIMUMS = {

    "originality": 7,
    "philosophical_depth": 7,
    "visual_strength": 7

}


def run_quality_gate(data):

    account_id = os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]

    token = os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/meta/"
        f"llama-3.1-8b-instruct"
    )

    scenes_for_judge = []

    for scene in data.get("scenes", []):

        visual = scene.get(
            "visual",
            {}
        )

        scenes_for_judge.append({

            "scene": scene.get(
                "scene"
            ),

            "voice_line": scene.get(
                "voice_line"
            ),

            "subject": visual.get(
                "subject"
            ),

            "action": visual.get(
                "action"
            ),

            "emotion": visual.get(
                "emotion"
            ),

            "environment": visual.get(
                "environment"
            ),

            "camera": visual.get(
                "camera"
            ),

            "composition": visual.get(
                "composition"
            )

        })

    judge_payload = {

        "messages": [

            {

                "role": "system",

                "content": """
You are a strict cinematic creative quality judge.

Evaluate a generated premium motivational YouTube Short.

You are NOT rewriting the piece.

You are judging whether it works as a high-retention motivational performance rather than a conventional story video, and whether it is specific enough to continue into expensive production.

Score each category from 1 to 10.

originality:
Does the concept, hook, motivational philosophy, performance format, and central thought feel genuinely fresh rather than like a reworded motivation template or another mini-story?

philosophical_depth:
Does the narration create a real internal shift through tension, contrast, emotional specificity, reflection, consequence, or a sharp reframe? Is the final insight earned by the preceding lines rather than generic advice?

visual_strength:
Do the scenes create premium cinematic imagery, specific actions, environments, symbolic meaning and compositions that amplify the motivational performance rather than merely decorate a narration?

repetition_risk:
How likely is the short to feel repetitive, generic or interchangeable with another motivational Short? Consider repeated opening patterns, predictable emotional arcs, generic phrases, interchangeable endings, and overused visual premises.

Pay special attention to:

- Concept strength: Is there one compelling human tension, contradiction, question, trade-off, or realization strong enough to carry the entire Short?
- The first sentence: does it create an immediate reason to continue without giving away the entire lesson?
- Curiosity architecture: is there a meaningful unanswered question, contradiction, or consequence that the narration resolves progressively?
- Emotional/intellectual progression: does each section add new meaning, pressure, evidence, contrast, or perspective instead of restating the same point?
- Specificity: concrete human stakes, precise observations, trade-offs, sensations, or symbolic details are stronger than vague encouragement.
- Payoff: does the ending make the opening more meaningful in retrospect and deliver a specific realization that feels earned?
- Rewatchability: is there a line, contrast, or idea that becomes more meaningful after the payoff without becoming confusing?
- Format diversity: does this feel like a genuinely different motivational performance rather than another person-overcomes-adversity story or another copy of the same motivational monologue pattern?
- Visual-semantic coherence: do the scenes reinforce the exact emotional and philosophical progression instead of decorating a generic speech?

Automatic warning signs:

- Generic openers such as "In life...", "Sometimes...", "Most people...", or "You need to..."
- Generic closers such as "Never give up" or "Keep going"
- A lesson stated before the viewer has a reason to care
- No clear unanswered tension after the opening
- A middle section that merely repeats the hook or thesis in new wording
- Recycled "darkness to light" or "fall then rise" structure without a fresh philosophy
- Traditional character-story structure used when a direct idea, contradiction, observation, or symbolic concept would be stronger
- Narration that could be swapped into another Short with almost no changes
- Long setup, backstory, or plot exposition before the motivational idea arrives
- A flat sequence of slogans with no escalation, contradiction, or perspective shift
- Final line that could close almost any motivational video

A high repetition_risk is BAD.

The final decision must be:

PASS

only when:

originality >= 7
philosophical_depth >= 7
visual_strength >= 7
repetition_risk <= 4

Otherwise:

REGENERATE

Return ONLY valid JSON.

Format:

{
    "originality": 0,
    "philosophical_depth": 0,
    "visual_strength": 0,
    "repetition_risk": 0,
    "final_decision": "PASS"
}
"""

            },

            {

                "role": "user",

                "content": json.dumps({

                    "title":
                    data.get(
                        "title",
                        ""
                    ),

                    "theme":
                    data.get(
                        "theme",
                        ""
                    ),

                    "hook":
                    data.get(
                        "hook",
                        ""
                    ),

                    "narration":
                    data.get(
                        "narration",
                        ""
                    ),

                    "creative_direction":
                    data.get(
                        "creative_direction",
                        {}
                    ),

                    "scenes":
                    scenes_for_judge

                }, ensure_ascii=False)

            }

        ],

        # Small judge response to reduce token usage
        "max_tokens": 500
    }

    response = requests.post(

        url,

        headers={

            "Authorization":
            f"Bearer {token}",

            "Content-Type":
            "application/json"

        },

        json=judge_payload,

        timeout=120

    )

    response.raise_for_status()

    result = response.json().get(
        "result"
    )

    if isinstance(result, dict):

        result = result.get(
            "response",
            result
        )

    quality = parse_json(
        result
    )

    if not isinstance(
        quality,
        dict
    ):

        raise Exception(
            "Quality gate returned invalid data"
        )

    try:

        originality = int(
            quality.get(
                "originality",
                0
            )
        )

        philosophical_depth = int(
            quality.get(
                "philosophical_depth",
                0
            )
        )

        visual_strength = int(
            quality.get(
                "visual_strength",
                0
            )
        )

        repetition_risk = int(
            quality.get(
                "repetition_risk",
                10
            )
        )

    except Exception:

        raise Exception(
            "Quality gate returned invalid scores"
        )

    # Clamp values safely to 1-10
    originality = max(
        1,
        min(10, originality)
    )

    philosophical_depth = max(
        1,
        min(10, philosophical_depth)
    )

    visual_strength = max(
        1,
        min(10, visual_strength)
    )

    repetition_risk = max(
        1,
        min(10, repetition_risk)
    )

    decision = "PASS"

    if originality < QUALITY_MINIMUMS["originality"]:

        decision = "REGENERATE"

    if philosophical_depth < QUALITY_MINIMUMS["philosophical_depth"]:

        decision = "REGENERATE"

    if visual_strength < QUALITY_MINIMUMS["visual_strength"]:

        decision = "REGENERATE"

    if repetition_risk > 4:

        decision = "REGENERATE"

    quality_result = {

        "originality":
        originality,

        "philosophical_depth":
        philosophical_depth,

        "visual_strength":
        visual_strength,

        "repetition_risk":
        repetition_risk,

        "final_decision":
        decision

    }

    # Save judge result into production brief
    data["quality_score"] = quality_result

    print(
        "Quality Score:"
    )

    print(
        f"  Originality: {originality}/10"
    )

    print(
        f"  Emotional Depth: {philosophical_depth}/10"
    )

    print(
        f"  Visual Strength: {visual_strength}/10"
    )

    print(
        f"  Repetition Risk: {repetition_risk}/10"
    )

    print(
        f"  Creative Decision: {decision}"
    )

    return decision == "PASS"


# =====================================
# PEXELS SEARCH
# =====================================

def _safe_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _video_candidate_score(video, target_duration=8):
    """Rank cinematic video candidates without changing the renderer."""
    width = _safe_number(video.get("width"))
    height = _safe_number(video.get("height"))
    duration = _safe_number(video.get("duration"))

    landscape_score = 1.0 if width > height else 0.0

    pixels = width * height
    if pixels >= 3840 * 2160:
        resolution_score = 1.0
    elif pixels >= 2560 * 1440:
        resolution_score = 0.92
    elif pixels >= 1920 * 1080:
        resolution_score = 0.82
    elif pixels > 0:
        resolution_score = min(
            0.75,
            pixels / (1920 * 1080) * 0.75
        )
    else:
        resolution_score = 0.0

    # Prefer longer usable cinematic clips while still allowing shorter clips.
    duration_score = min(
        1.0,
        max(0.0, duration / max(target_duration, 1))
    )

    # Prefer candidates with a high-quality preview picture.
    preview_score = 0.0
    for picture in video.get("video_pictures", []) or []:
        pw = _safe_number(picture.get("width"))
        ph = _safe_number(picture.get("height"))
        preview_pixels = pw * ph
        preview_score = max(
            preview_score,
            min(
                1.0,
                preview_pixels / (1920 * 1080)
            )
            if preview_pixels > 0 else 0.0
        )

    return (
        resolution_score * 0.40
        + duration_score * 0.30
        + landscape_score * 0.20
        + preview_score * 0.10
    )


def _select_best_video_file(video):
    """Pick the strongest landscape HD/4K source file."""
    files = video.get("video_files", []) or []

    candidates = []
    for file_item in files:
        width = _safe_number(file_item.get("width"))
        height = _safe_number(file_item.get("height"))

        if width <= 0 or height <= 0:
            continue

        landscape = width >= height
        quality = str(
            file_item.get("quality", "")
        ).lower()

        resolution_score = (
            min(
                1.0,
                (width * height) / (3840 * 2160)
            )
        )

        quality_bonus = 0.0
        if quality == "uhd":
            quality_bonus = 1.0
        elif quality == "hd":
            quality_bonus = 0.85

        score = (
            resolution_score * 0.75
            + quality_bonus * 0.15
            + (0.10 if landscape else 0.0)
        )

        candidates.append(
            (score, file_item)
        )

    if not candidates:
        return {}

    candidates.sort(
        key=lambda item: item[0],
        reverse=True
    )

    return candidates[0][1]


def pexels_search(query):
    key = os.environ[
        "PEXELS_API_KEY"
    ]

    try:
        response = requests.get(
            "https://api.pexels.com/videos/search",
            headers={
                "Authorization":
                key
            },
            params={
                "query":
                query,

                # More candidates so the ranking logic can choose better footage.
                "per_page":
                20
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        ranked = []

        for video in data.get(
            "videos",
            []
        ):
            best_file = _select_best_video_file(video)

            candidate = {
                "id":
                video.get(
                    "id"
                ),

                "url":
                video.get(
                    "url"
                ),

                "duration":
                video.get(
                    "duration"
                ),

                "width":
                video.get(
                    "width"
                ),

                "height":
                video.get(
                    "height"
                ),

                "quality":
                best_file.get(
                    "quality"
                ),

                "video_file":
                best_file.get(
                    "link"
                ),

                "video_file_width":
                best_file.get(
                    "width"
                ),

                "video_file_height":
                best_file.get(
                    "height"
                ),

                "preview":
                (
                    (video.get("video_pictures") or [{}])[0]
                    .get("picture")
                )
            }

            candidate["_score"] = _video_candidate_score(
                video
            )

            ranked.append(
                candidate
            )

        ranked.sort(
            key=lambda item: item["_score"],
            reverse=True
        )

        results = []

        for candidate in ranked:
            candidate.pop(
                "_score",
                None
            )
            results.append(
                candidate
            )

        return results

    except Exception as e:
        print(
            "Pexels video search failed:",
            e
        )
        return []


def _image_candidate_score(photo):
    """Rank landscape photo candidates by resolution and preview quality."""
    width = _safe_number(photo.get("width"))
    height = _safe_number(photo.get("height"))

    landscape_score = 1.0 if width >= height else 0.0

    pixels = width * height
    resolution_score = min(
        1.0,
        pixels / (3840 * 2160)
    ) if pixels > 0 else 0.0

    src = photo.get(
        "src",
        {}
    )

    preview_score = 1.0 if src.get(
        "large2x"
    ) else (
        0.7 if src.get("large")
        else 0.0
    )

    return (
        resolution_score * 0.65
        + landscape_score * 0.25
        + preview_score * 0.10
    )


def pexels_image_search(query):
    key = os.environ[
        "PEXELS_API_KEY"
    ]

    try:
        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers={
                "Authorization":
                key
            },
            params={
                "query":
                query,

                "orientation":
                "landscape",

                "per_page":
                20
            },
            timeout=30
        )

        response.raise_for_status()

        data = response.json()

        ranked = []

        for photo in data.get(
            "photos",
            []
        ):
            ranked.append(
                (
                    _image_candidate_score(photo),
                    {
                        "id":
                        photo.get(
                            "id"
                        ),

                        "url":
                        photo.get(
                            "url"
                        ),

                        "width":
                        photo.get(
                            "width"
                        ),

                        "height":
                        photo.get(
                            "height"
                        ),

                        "alt":
                        photo.get(
                            "alt"
                        ),

                        "image":
                        (
                            photo.get(
                                "src",
                                {}
                            ).get(
                                "original"
                            )
                        ),

                        "preview":
                        (
                            photo.get(
                                "src",
                                {}
                            ).get(
                                "large2x"
                            )
                        )
                    }
                )
            )

        ranked.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            item[1]
            for item in ranked
        ]

    except Exception as e:
        print(
            "Pexels image search failed:",
            e
        )
        return []


# =====================================
# LIGHTWEIGHT SEO METADATA
# Generated from the actual story without another API call.
# =====================================

def _seo_tokens(*values):
    tokens = []
    seen = set()
    stop_words = {
        "the", "and", "for", "with", "from", "that", "this",
        "your", "you", "our", "are", "can", "but", "into", "about",
        "what", "when", "where", "how", "why", "its", "it's",
        "a", "an", "to", "of", "in", "on", "is", "be", "it",
    }
    for value in values:
        for token in re.findall(r"[A-Za-z0-9']+", str(value or "").lower()):
            if len(token) < 3 or token in stop_words or token in seen:
                continue
            seen.add(token)
            tokens.append(token)
    return tokens


def build_seo_metadata(data):
    title = re.sub(r"\s+", " ", str(data.get("title", "Motivational Short")).strip())
    theme = str(data.get("theme", "")).strip()
    creative = data.get("creative_direction", {}) or {}
    philosophy = str(creative.get("philosophical_theme", "")).strip()
    visual_style = str(creative.get("visual_style", "")).strip()
    narration = re.sub(r"\s+", " ", str(data.get("narration", "")).strip())

    keyword_pool = _seo_tokens(
        title,
        theme,
        philosophy,
        visual_style,
        data.get("hook", ""),
    )

    # Keep a compact set of natural, high-intent terms, then add only a few
    # topic-specific terms from the actual generated concept.
    keywords = [
        "motivational speech",
        "motivation",
        "mindset",
    ]

    topic_phrases = [
        ("discipline", {"discipline"}),
        ("overcoming fear", {"fear", "overcoming"}),
        ("failure and growth", {"failure", "growth"}),
        ("resilience", {"resilience", "strength"}),
        ("self mastery", {"mastery", "self"}),
        ("personal growth", {"growth", "journey", "transformation"}),
        ("stoic philosophy", {"stoic", "stoicism", "philosophy"}),
    ]
    for phrase, triggers in topic_phrases:
        if any(trigger in keyword_pool for trigger in triggers):
            keywords.append(phrase)

    for token in keyword_pool:
        if token not in {"motivational", "speech"} and token not in " ".join(keywords):
            keywords.append(token)
        if len(keywords) >= 10:
            break

    primary_tags = [
        "motivation",
        "motivationalshorts",
        "mindset",
    ]
    topic_map = {
        "discipline": "discipline",
        "stoic": "stoicism",
        "stoicism": "stoicism",
        "resilience": "resilience",
        "success": "success",
        "self": "selfmastery",
        "growth": "personalgrowth",
        "fear": "overcomefear",
        "strength": "innerstrength",
    }
    for token in keyword_pool:
        tag = topic_map.get(token)
        if tag and tag not in primary_tags:
            primary_tags.append(tag)
        if len(primary_tags) >= 7:
            break

    description_intro = narration
    if len(description_intro) > 420:
        description_intro = description_intro[:417].rsplit(" ", 1)[0] + "..."

    subject = theme.lower() or philosophy.lower() or "mindset, discipline, and personal growth"
    style_phrase = visual_style.lower() or "cinematic"
    description = (
        f"{description_intro}\n\n"
        f"This cinematic motivational short explores {subject}. "
        f"It combines focused narration with a visual style of {style_phrase}, designed to reinforce the message about mindset, discipline, and personal growth."
    )

    return {
        "title": title,
        "description": description,
        "keywords": keywords[:12],
        "hashtags": [f"#{tag}" for tag in primary_tags[:7]],
    }


# =====================================
# MAIN PIPELINE
# =====================================

print(
    "Starting Motivational Factory V5.3"
)


final = None
last_error = ""


# =====================================
# GENERATION + STRUCTURAL VALIDATION
# + CREATIVE QUALITY GATE
# =====================================

for attempt in range(5):

    try:

        print(
            "Generation attempt",
            attempt + 1
        )

        raw = cloudflare_generate(
            last_error
        )

        data = parse_json(
            raw
        )

        # =================================
        # STEP 1:
        # Structural / cinematic validation
        # =================================

        if not validate(data):

            last_error = (
                "Structural validation failed. "
                "Create a valid cinematic original "
                "motivational concept with exactly 6 complete scenes "
                "and strong idea-connected visuals."
            )

            print(
                "ERROR:",
                last_error
            )

            time.sleep(5)

            continue

        # =================================
        # STEP 2:
        # V5.3 Creative Quality Gate
        # =================================

        print(
            "Running V5.3 Creative Quality Gate..."
        )

        quality_passed = run_quality_gate(
            data
        )

        if not quality_passed:

            quality = data.get(
                "quality_score",
                {}
            )

            last_error = (

                "Creative Quality Gate rejected "
                "the previous generation. "

                f"Originality="
                f"{quality.get('originality', 0)}/10, "

                f"Emotional depth="
                f"{quality.get('philosophical_depth', 0)}/10, "

                f"Visual strength="
                f"{quality.get('visual_strength', 0)}/10, "

                f"Repetition risk="
                f"{quality.get('repetition_risk', 10)}/10. "

                "Create a substantially different "
                "premium motivational concept. Use a different "
                "performance format, central tension, emotional "
                "progression, hook logic, escalation, and payoff. "
                "Avoid traditional story structures when a direct "
                "motivational idea would be stronger. Avoid generic "
                "motivation, repeated visual structures, flat lists "
                "of slogans, and interchangeable scenes. Make every "
                "narration beat add new meaning and make the final "
                "line specifically earned."
            )

            print(
                "Creative Quality Gate: REGENERATE"
            )

            time.sleep(5)

            continue

        print(
            "Creative Quality Gate: PASS"
        )

        final = data

        break

    except Exception as e:

        print(
            "ERROR:",
            e
        )

        last_error = str(e)

        time.sleep(5)


if final is None:

    raise Exception(
        "Could not create valid high-quality cinematic Short"
    )


# =====================================
# SAVE PRODUCTION BRIEF
# =====================================


final["seo"] = build_seo_metadata(final)
final["description"] = final["seo"]["description"]
final["keywords"] = final["seo"]["keywords"]
final["hashtags"] = final["seo"]["hashtags"]


voice_profile_name, selected_voice_profile = select_voice_profile(
    final.get("voice_direction", {}),
    final
)

selected_voice = selected_voice_profile.get(
    "voice",
    "am_adam"
)

final["voice_profile_selected"] = {
    "profile":
    voice_profile_name,

    "voice":
    selected_voice,

    "description":
    selected_voice_profile.get(
        "description",
        ""
    ),

    "delivery": {
        "pace":
        final.get(
            "voice_direction",
            {}
        ).get(
            "pace",
            selected_voice_profile.get(
                "pace",
                ""
            )
        ),

        "emotion":
        final.get(
            "voice_direction",
            {}
        ).get(
            "emotion",
            selected_voice_profile.get(
                "emotion",
                ""
            )
        ),

        "intensity":
        final.get(
            "voice_direction",
            {}
        ).get(
            "intensity",
            selected_voice_profile.get(
                "intensity",
                ""
            )
        )
    }
}


with open(

    OUTPUT / "production_brief.json",

    "w",

    encoding="utf-8"

) as f:

    json.dump(

        final,

        f,

        indent=2,

        ensure_ascii=False

    )


print(
    "Production brief saved"
)


# =====================================
# PEXELS CINEMATIC ASSETS
# =====================================

assets = {
    "videos": [],
    "images": []
}


for scene in final["scenes"]:

    print(

        "Searching cinematic asset:",

        scene["pexels_query"]

    )

    videos = pexels_search(

        scene["pexels_query"]

    )

    images = pexels_image_search(

        scene["pexels_query"]

    )

    assets["videos"].append({

        "scene":
        scene["scene"],

        "visual":
        scene["visual"],

        "pexels_query":
        scene["pexels_query"],

        "videos":
        videos

    })

    assets["images"].append({

        "scene":
        scene["scene"],

        "visual":
        scene["visual"],

        "pexels_query":
        scene["pexels_query"],

        "images":
        images

    })


with open(

    OUTPUT / "visual_assets.json",

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
    "Visual assets saved"
)


# =====================================
# VOICE GENERATION
# =====================================

narration = final["narration"]

print(
    "Generating cinematic voice with profile:",
    voice_profile_name,
    "->",
    selected_voice
)


try:

    generate_voice(
        narration,
        voice_profile=selected_voice
    )

except Exception as voice_error:

    print(
        "Selected voice failed:",
        voice_error
    )

    print(
        "Falling back to am_adam..."
    )

    generate_voice(
        narration,
        voice_profile="am_adam"
    )


print(
    "Voice completed"
)


# =====================================
# CAPTION GENERATION
# =====================================

print(
    "Creating caption plan..."
)


create_caption_plan(
    narration
)


print(
    "Caption plan completed"
)


# =====================================
# V6 VIDEO RENDERER
# =====================================

print(
    "Starting V6 cinematic renderer..."
)

render_succeeded = render()
seo_succeeded = False

if render_succeeded:

    print(
        "Video rendering completed"
    )

    # =====================================
    # POST-RENDER SEO GENERATION
    # =====================================

    print(
        "Generating platform SEO metadata..."
    )

    try:

        seo_metadata = generate_seo_metadata(
            final
        )

        seo_succeeded = True

        print_seo_metadata_summary(
            seo_metadata
        )

    except Exception as seo_error:

        print(
            "WARNING: SEO generation failed; video output preserved:",
            seo_error
        )

else:

    print(
        "WARNING: Video rendering did not complete successfully; "
        "SEO generation skipped."
    )


# =====================================
# SAVE GENERATION MEMORY
# =====================================

save_history(
    final
)


render_status = (
    "✓ final_short.mp4 generated"
    if render_succeeded
    else "✗ final_short.mp4 was not generated"
)

seo_status = (
    "✓ SEO metadata generated"
    if seo_succeeded
    else (
        "⚠ SEO metadata unavailable"
        if render_succeeded
        else "— SEO metadata skipped because rendering failed"
    )
)

workflow_status = (
    "COMPLETE"
    if render_succeeded
    else "FINISHED WITH WARNINGS"
)

print(
    f"""
=================================

MOTIVATIONAL FACTORY V5.3 {workflow_status}

Generated:

✓ Production Brief
✓ Cinematic Visual Plan
✓ Creative Quality Gate
✓ Quality Score
✓ Pexels Assets
✓ Kokoro Voice
✓ Caption Plan
✓ Creative History

Quality Gate:

✓ Originality checked
✓ Emotional depth checked
✓ Visual strength checked
✓ Repetition risk checked

Final Outputs:

{render_status}
{seo_status}

=================================
"""
)

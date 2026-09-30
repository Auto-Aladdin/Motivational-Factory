import json
import re
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

CAPTION_OUTPUT = OUTPUT / "caption_plan.json"


# =====================================================
# PREMIUM CAPTION COLOR SYSTEM
# =====================================================

COLORS = {

    "normal": "#FFFFFF",
    "highlight": "#FFD447",
    "pain": "#FF5555",
    "hope": "#45E6FF"

}


# =====================================================
# WORD CLASSIFICATION
# =====================================================

HIGH_IMPACT_WORDS = {

    "discipline",
    "success",
    "failure",
    "fear",
    "dream",
    "focus",
    "growth",
    "change",
    "future",
    "strength",
    "power",
    "believe",
    "confidence",
    "never",
    "impossible",
    "winner",
    "quit",
    "sacrifice",
    "purpose"

}


PAIN_WORDS = {

    "failure",
    "lost",
    "pain",
    "struggle",
    "fear",
    "broken",
    "hurt",
    "quit"

}


HOPE_WORDS = {

    "hope",
    "future",
    "dream",
    "growth",
    "believe",
    "success",
    "confidence"

}


# =====================================================
# TEXT CLEANING
# =====================================================

def clean_text(text):

    text = str(text).strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text



def tokenize(text):

    return re.findall(
        r"\b[\w']+\b",
        text
    )


# =====================================================
# WORD STYLE
# =====================================================

def detect_style(word):

    lower = word.lower()


    if lower in PAIN_WORDS:

        return {
            "style":"pain",
            "color":COLORS["pain"],
            "animation":"impact_pop"
        }


    if lower in HOPE_WORDS:

        return {
            "style":"hope",
            "color":COLORS["hope"],
            "animation":"soft_glow"
        }


    if lower in HIGH_IMPACT_WORDS:

        return {
            "style":"highlight",
            "color":COLORS["highlight"],
            "animation":"impact_pop"
        }


    return {

        "style":"normal",
        "color":COLORS["normal"],
        "animation":"fade"

    }



# =====================================================
# OPTIONAL AUDIO ALIGNMENT
# =====================================================

def get_word_timestamps(
        audio_path,
        language="en"
):

    """
    Uses local Whisper alignment.

    Returns:

    [
       {
        word:"",
        start:0.0,
        end:0.5
       }
    ]

    """

    try:

        from faster_whisper import WhisperModel


        model = WhisperModel(
            "small",
            compute_type="int8"
        )


        segments, info = model.transcribe(

            audio_path,

            word_timestamps=True,

            language=language

        )


        words=[]


        for segment in segments:

            if segment.words:

                for item in segment.words:

                    words.append({

                        "word":
                        item.word.strip(),

                        "start":
                        round(
                            item.start,
                            3
                        ),

                        "end":
                        round(
                            item.end,
                            3
                        )

                    })


        return words


    except Exception as e:

        print(
            "Whisper alignment unavailable:",
            e
        )

        return []



# =====================================================
# SMART CAPTION GROUPING
# =====================================================

def create_groups(
        words,
        max_words=5
):

    groups=[]

    current=[]


    for word in words:


        current.append(word)


        text = " ".join(
            [
                w["word"]
                for w in current
            ]
        )


        # Natural breaks

        if (

            len(current)>=max_words

            or text.endswith(
                (
                    ".",
                    ",",
                    "!",
                    "?"
                )
            )

        ):

            groups.append(
                current
            )

            current=[]


    if current:

        groups.append(
            current
        )


    return groups



# =====================================================
# FALLBACK TIMING
# =====================================================

def fallback_alignment(words):

    result=[]

    time=0


    for word in words:

        duration=0.35


        result.append({

            "word":word,

            "start":
            round(
                time,
                3
            ),

            "end":
            round(
                time+duration,
                3
            )

        })


        time+=duration


    return result



# =====================================================
# MAIN CAPTION GENERATOR
# =====================================================

def create_caption_plan(
        narration,
        audio_path=None
):


    print(
        "Creating cinematic caption plan..."
    )


    narration = clean_text(
        narration
    )

    # The factory already creates voice.wav immediately before the caption
    # stage. When the caller does not explicitly pass an audio path, use that
    # real generated audio so word timings come from the spoken voice rather
    # than the old fixed-duration fallback. This does not change pipeline
    # order or any upstream generation logic.
    if audio_path is None:

        default_audio = CAPTION_OUTPUT.parent / "voice.wav"

        if default_audio.exists():
            audio_path = str(default_audio)


    text_words = tokenize(
        narration
    )


    aligned_words=[]


    if audio_path:

        aligned_words = get_word_timestamps(
            audio_path
        )


    if not aligned_words:

        aligned_words = fallback_alignment(
            text_words
        )



    groups = create_groups(
        aligned_words
    )



    captions=[]


    for index, group in enumerate(groups):


        styled_words=[]


        for item in group:


            style = detect_style(
                item["word"]
            )


            styled_words.append({

                "word":
                item["word"].upper(),

                "start":
                item["start"],

                "end":
                item["end"],

                "style":
                style["style"],

                "color":
                style["color"],

                "animation":
                style["animation"]

            })


        captions.append({

            "id":
            index+1,


            "text":
            " ".join(
                [
                    x["word"]
                    for x in styled_words
                ]
            ),


            "start":
            group[0]["start"],


            "end":
            group[-1]["end"],


            "words":
            styled_words,


            "font":
            "Montserrat ExtraBold",


            "position":
            "lower_center",


            "animation":{

                "entrance":
                "smooth_scale",

                "exit":
                "fade",

                "emphasis":
                any(
                    x["style"] != "normal"
                    for x in styled_words
                )

            }

        })



    with open(

        CAPTION_OUTPUT,

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            captions,

            f,

            indent=2,

            ensure_ascii=False

        )


    print(

        "Caption plan saved:",

        CAPTION_OUTPUT

    )


    return captions

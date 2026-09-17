import json
import re
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


CAPTION_OUTPUT = OUTPUT / "caption_plan.json"



# =====================================================
# COLOR SYSTEM
# =====================================================

COLORS = {

    "normal":
    "#FFFFFF",

    "highlight":
    "#F3CE32",

    "pain":
    "#FF4D4D",

    "hope":
    "#45E6FF"

}



# =====================================================
# WORD CLASSIFICATION
# =====================================================

HIGH_IMPACT_WORDS = [

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
    "sacrifice"

]



PAIN_WORDS = [

    "failure",
    "lost",
    "pain",
    "struggle",
    "fear",
    "broken",
    "hurt",
    "quit"

]



HOPE_WORDS = [

    "hope",
    "future",
    "dream",
    "growth",
    "believe",
    "success",
    "confidence"

]



# =====================================================
# CLEAN TEXT
# =====================================================

def clean_text(text):

    text = text.strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text



# =====================================================
# SPLIT WORDS
# =====================================================

def tokenize(text):

    return re.findall(
        r"\b[\w']+\b",
        text
    )



# =====================================================
# STYLE DETECTION
# =====================================================

def detect_style(word):

    lower = word.lower()



    if lower in PAIN_WORDS:

        return {

            "style":
            "pain",

            "color":
            COLORS["pain"]

        }



    if lower in HOPE_WORDS:

        return {

            "style":
            "hope",

            "color":
            COLORS["hope"]

        }



    if lower in HIGH_IMPACT_WORDS:

        return {

            "style":
            "highlight",

            "color":
            COLORS["highlight"]

        }



    return {

        "style":
        "normal",

        "color":
        COLORS["normal"]

    }



# =====================================================
# CAPTION GROUPING
# =====================================================

def create_caption_groups(words):


    groups=[]


    current=[]


    for word in words:


        current.append(word)



        if len(current)>=3:


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
# CREATE CAPTION PLAN
# =====================================================

def create_caption_plan(narration):


    print(
        "Creating caption plan..."
    )


    narration = clean_text(
        narration
    )



    words = tokenize(
        narration
    )



    groups = create_caption_groups(
        words
    )



    captions=[]



    current_time = 0.0



    for index,group in enumerate(groups):


        duration = max(

            1.2,

            len(group)*0.35

        )


        styled_words=[]



        for word in group:


            style = detect_style(
                word
            )


            styled_words.append(

                {

                "word":
                word.upper(),

                "style":
                style["style"],

                "color":
                style["color"]

                }

            )



        captions.append(

            {

            "id":
            index+1,

            "text":
            " ".join(group).upper(),

            "start":
            round(
                current_time,
                2
            ),

            "end":
            round(
                current_time + duration,
                2
            ),

            "words":
            styled_words,

            "font":
            "Montserrat ExtraBold",

            "position":
            "center"

            }

        )



        current_time += duration





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

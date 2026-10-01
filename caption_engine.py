import json
import re
import wave
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

def _audio_duration(path):

    try:

        with wave.open(str(path), "rb") as audio:

            frames = audio.getnframes()
            rate = audio.getframerate()

        if rate:
            return frames / float(rate)

    except Exception as e:

        print(
            "Audio duration read failed:",
            e
        )

    return 0.0


def _sentence_parts_alignment(
        narration,
        audio_path=None
):

    """
    Use the exact sentence boundaries produced by voice_engine.py.

    The voice engine creates one voice_part_N.wav for every narration sentence
    and inserts the real silence_N.wav after it. Those files therefore give us
    the exact sentence clock of the final voice.wav even when Whisper is not
    available. Word timings are then distributed across the actual sentence
    duration instead of using the obsolete fixed 0.35s-per-word clock.
    """

    if not audio_path:
        return []

    audio_path = Path(audio_path)
    output_dir = audio_path.parent

    sentences = re.split(
        r'(?<=[.!?])\s+',
        str(narration or '').strip()
    )
    sentences = [s for s in sentences if s]

    if not sentences:
        return []

    aligned = []
    cursor = 0.0

    for index, sentence in enumerate(sentences):

        part = output_dir / f"voice_part_{index}.wav"
        if not part.exists():
            return []

        part_duration = _audio_duration(part)
        if part_duration <= 0:
            return []

        sentence_words = tokenize(sentence)
        if not sentence_words:
            return []

        weights = [
            max(
                1,
                len(
                    re.sub(
                        r"[^a-zA-Z0-9']+",
                        "",
                        word
                    )
                )
            )
            for word in sentence_words
        ]

        total_weight = float(sum(weights)) or float(len(sentence_words))
        word_cursor = cursor

        for word_index, (word, weight) in enumerate(
                zip(sentence_words, weights)
        ):

            if word_index == len(sentence_words) - 1:
                word_end = cursor + part_duration
            else:
                word_end = (
                    word_cursor
                    + part_duration * (weight / total_weight)
                )

            aligned.append({
                "word": word,
                "start": round(word_cursor, 3),
                "end": round(
                    max(word_cursor + 0.01, word_end),
                    3
                )
            })

            word_cursor = word_end

        silence = output_dir / f"silence_{index}.wav"
        if silence.exists():
            cursor += part_duration + _audio_duration(silence)
        else:
            cursor += part_duration

    return aligned


def fallback_alignment(words, duration=None):

    """Fill the supplied real audio duration using text-length weights."""

    if not words:
        return []

    if duration is None or duration <= 0:
        duration = 0.35 * len(words)

    weights = [
        max(
            1,
            len(
                re.sub(
                    r"[^a-zA-Z0-9']+",
                    "",
                    str(word)
                )
            )
        )
        for word in words
    ]

    total_weight = float(sum(weights)) or float(len(words))
    result = []
    cursor = 0.0

    for index, (word, weight) in enumerate(zip(words, weights)):

        if index == len(words) - 1:
            end = float(duration)
        else:
            end = (
                cursor
                + float(duration) * (weight / total_weight)
            )

        result.append({
            "word": word,
            "start": round(cursor, 3),
            "end": round(
                max(cursor + 0.01, end),
                3
            )
        })

        cursor = end

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

        aligned_words = _sentence_parts_alignment(
            narration,
            audio_path
        )

    if not aligned_words:

        audio_duration = (
            _audio_duration(audio_path)
            if audio_path
            else 0.0
        )

        aligned_words = fallback_alignment(
            text_words,
            audio_duration
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

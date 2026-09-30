import json
import re
import wave
from pathlib import Path
from difflib import SequenceMatcher


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


def normalize_word(word):

    word = str(word or "").lower().strip()

    word = word.replace(
        "’",
        "'"
    )

    return re.sub(
        r"[^a-z0-9']+",
        "",
        word
    )


# =====================================================
# WORD STYLE
# =====================================================

def detect_style(word):

    lower = normalize_word(word)

    if lower in PAIN_WORDS:

        return {
            "style": "pain",
            "color": COLORS["pain"],
            "animation": "impact_pop"
        }

    if lower in HOPE_WORDS:

        return {
            "style": "hope",
            "color": COLORS["hope"],
            "animation": "soft_glow"
        }

    if lower in HIGH_IMPACT_WORDS:

        return {
            "style": "highlight",
            "color": COLORS["highlight"],
            "animation": "impact_pop"
        }

    return {

        "style": "normal",
        "color": COLORS["normal"],
        "animation": "fade"

    }


# =====================================================
# AUDIO HELPERS
# =====================================================

def get_wav_duration(audio_path):

    try:

        with wave.open(
            str(audio_path),
            "rb"
        ) as audio:

            frames = audio.getnframes()

            rate = audio.getframerate()

            if rate <= 0:
                return 0.0

            return frames / float(rate)

    except Exception:

        return 0.0


def numbered_audio_parts():

    parts = []

    for path in OUTPUT.glob(
        "voice_part_*.wav"
    ):

        match = re.search(
            r"voice_part_(\d+)\.wav$",
            path.name
        )

        if not match:
            continue

        parts.append(
            (
                int(match.group(1)),
                path
            )
        )

    parts.sort(
        key=lambda item: item[0]
    )

    return parts


def silence_duration(index):

    path = OUTPUT / f"silence_{index}.wav"

    if not path.exists():
        return 0.0

    return get_wav_duration(
        path
    )


# =====================================================
# WHISPER MODEL
# =====================================================

def load_whisper_model():

    from faster_whisper import WhisperModel

    return WhisperModel(
        "small.en",
        device="cpu",
        compute_type="int8"
    )


# =====================================================
# REAL AUDIO WORD TIMESTAMPS
# =====================================================

def transcribe_audio(
        model,
        audio_path,
        expected_text=None
):

    options = {

        "word_timestamps": True,

        "language": "en",

        "beam_size": 5,

        "best_of": 5,

        "temperature": 0,

        "condition_on_previous_text": False,

        "vad_filter": False

    }

    if expected_text:

        options["initial_prompt"] = expected_text

    segments, _ = model.transcribe(
        str(audio_path),
        **options
    )

    words = []

    for segment in segments:

        if not segment.words:
            continue

        for item in segment.words:

            token = str(
                item.word or ""
            ).strip()

            if not token:
                continue

            try:

                start = float(
                    item.start
                )

                end = float(
                    item.end
                )

            except (
                TypeError,
                ValueError
            ):

                continue

            if end < start:
                end = start

            words.append({

                "word": token,

                "start": start,

                "end": end

            })

    return words


# =====================================================
# WEIGHTED ALIGNMENT FOR RARE TRANSCRIPTION DIFFERENCES
# =====================================================

def weighted_split(
        start,
        end,
        words
):

    if not words:
        return []

    start = float(start)

    end = max(
        start,
        float(end)
    )

    weights = [

        max(
            1,
            len(
                normalize_word(word)
            )
        )

        for word in words

    ]

    total = float(
        sum(weights)
    ) or float(
        len(words)
    )

    result = []

    cursor = start

    for index, weight in enumerate(weights):

        if index == len(words) - 1:

            next_cursor = end

        else:

            next_cursor = (

                cursor
                +
                (end - start)
                *
                (weight / total)

            )

        result.append(
            (
                cursor,
                next_cursor
            )
        )

        cursor = next_cursor

    return result


# =====================================================
# MAP WHISPER TIMINGS TO EXACT NARRATION WORDS
# =====================================================

def align_transcript_to_text(
        expected_text,
        transcript_words,
        audio_duration
):

    target_words = tokenize(
        expected_text
    )

    transcript_words = [

        word

        for word in transcript_words

        if normalize_word(
            word.get(
                "word",
                ""
            )
        )

    ]

    if not target_words or not transcript_words:

        return [], 0.0

    target_normalized = [

        normalize_word(word)

        for word in target_words

    ]

    transcript_normalized = [

        normalize_word(
            word.get(
                "word",
                ""
            )
        )

        for word in transcript_words

    ]

    matcher = SequenceMatcher(

        None,

        target_normalized,

        transcript_normalized,

        autojunk=False

    )

    opcodes = matcher.get_opcodes()

    exact_matches = sum(

        i2 - i1

        for tag, i1, i2, j1, j2
        in opcodes

        if tag == "equal"

    )

    match_ratio = (

        exact_matches
        /
        float(
            max(
                1,
                len(target_words)
            )
        )

    )

    aligned = [
        None
        for _ in target_words
    ]

    for (
        tag,
        i1,
        i2,
        j1,
        j2
    ) in opcodes:

        if tag == "equal":

            for (
                target_index,
                transcript_index
            ) in zip(

                range(i1, i2),

                range(j1, j2)

            ):

                source = transcript_words[
                    transcript_index
                ]

                start = max(
                    0.0,
                    float(
                        source["start"]
                    )
                )

                end = max(
                    start + 0.005,
                    float(
                        source["end"]
                    )
                )

                if audio_duration > 0:

                    start = min(
                        start,
                        audio_duration
                    )

                    end = min(
                        end,
                        audio_duration
                    )

                    end = max(
                        start + 0.005,
                        end
                    )

                aligned[
                    target_index
                ] = (
                    start,
                    end
                )

        elif (
            tag == "replace"
            and j2 > j1
        ):

            start = float(
                transcript_words[j1][
                    "start"
                ]
            )

            end = float(
                transcript_words[j2 - 1][
                    "end"
                ]
            )

            split = weighted_split(

                start,

                end,

                target_words[
                    i1:i2
                ]

            )

            for offset, pair in enumerate(
                split
            ):

                aligned[
                    i1 + offset
                ] = pair

    # -------------------------------------------------
    # FILL UNMATCHED RANGES BETWEEN REAL AUDIO ANCHORS
    # -------------------------------------------------

    index = 0

    while index < len(aligned):

        if aligned[index] is not None:

            index += 1

            continue

        run_start = index

        while (
            index < len(aligned)
            and aligned[index] is None
        ):

            index += 1

        run_end = index

        left_end = 0.0

        if (
            run_start > 0
            and aligned[
                run_start - 1
            ] is not None
        ):

            left_end = aligned[
                run_start - 1
            ][1]

        right_start = float(
            audio_duration
        )

        if (
            run_end < len(aligned)
            and aligned[run_end] is not None
        ):

            right_start = aligned[
                run_end
            ][0]

        if right_start < left_end:

            right_start = left_end

        split = weighted_split(

            left_end,

            right_start,

            target_words[
                run_start:run_end
            ]

        )

        for offset, pair in enumerate(
            split
        ):

            aligned[
                run_start + offset
            ] = pair

    # -------------------------------------------------
    # FINAL MONOTONIC TIMESTAMP PASS
    # -------------------------------------------------

    result = []

    previous_end = 0.0

    for word, pair in zip(
        target_words,
        aligned
    ):

        if pair is None:

            start = previous_end

            end = (
                min(
                    audio_duration,
                    start + 0.01
                )
                if audio_duration > 0
                else
                start + 0.01
            )

        else:

            start, end = pair

            start = max(
                previous_end,
                float(start)
            )

            end = max(
                start + 0.005,
                float(end)
            )

            if audio_duration > 0:

                start = min(
                    start,
                    audio_duration
                )

                end = min(
                    end,
                    audio_duration
                )

                end = max(
                    start + 0.005,
                    end
                )

        result.append({

            "word": word,

            "start": round(
                start,
                3
            ),

            "end": round(
                end,
                3
            )

        })

        previous_end = end

    return (
        result,
        match_ratio
    )


def get_word_timestamps(
        audio_path,
        language="en",
        expected_text=None
):

    model = load_whisper_model()

    return transcribe_audio(

        model,

        audio_path,

        expected_text=expected_text

    )


# =====================================================
# SENTENCE-LEVEL AUDIO ALIGNMENT
# =====================================================

def align_from_sentence_parts(
        narration,
        model
):

    """
    IMPORTANT:

    voice_engine.py creates:

        voice_part_0.wav
        silence_0.wav
        voice_part_1.wav
        silence_1.wav
        ...

    The final voice.wav is literally those files concatenated together.

    Therefore each sentence is aligned against its exact original audio part,
    then its position is restored using the actual generated silence duration.

    This prevents cumulative forward/backward caption drift.
    """

    sentences = [

        sentence.strip()

        for sentence
        in re.split(
            r"(?<=[.!?])\s+",
            narration
        )

        if sentence.strip()

    ]

    parts = numbered_audio_parts()

    if (
        not sentences
        or len(parts) < len(sentences)
    ):

        return [], 0.0

    all_words = []

    cursor = 0.0

    ratios = []

    for index, sentence in enumerate(
        sentences
    ):

        _, audio_part = parts[index]

        part_duration = get_wav_duration(
            audio_part
        )

        if part_duration <= 0:

            return [], 0.0

        transcript = transcribe_audio(

            model,

            audio_part,

            expected_text=sentence

        )

        aligned, ratio = align_transcript_to_text(

            sentence,

            transcript,

            part_duration

        )

        if not aligned:

            return [], 0.0

        ratios.append(
            ratio
        )

        for word in aligned:

            absolute_start = max(

                0.0,

                cursor
                +
                word["start"]

            )

            absolute_end = max(

                absolute_start + 0.005,

                cursor
                +
                word["end"]

            )

            all_words.append({

                "word":
                word["word"],

                "start":
                round(
                    absolute_start,
                    3
                ),

                "end":
                round(
                    absolute_end,
                    3
                )

            })

        # EXACT SAME ORDER USED BY voice_engine.py:
        #
        # voice_part_N
        # silence_N
        #
        # Then the next voice_part starts.
        cursor += part_duration

        cursor += silence_duration(
            index
        )

    average_ratio = (

        sum(ratios)
        /
        max(
            1,
            len(ratios)
        )

    )

    return (
        all_words,
        average_ratio
    )


# =====================================================
# SMART CAPTION GROUPING
# =====================================================

def create_groups(
        words,
        max_words=5
):

    groups = []

    current = []

    for word in words:

        current.append(
            word
        )

        # Preserve the original five-word caption grouping.
        # Timing is now supplied by the actual spoken audio.
        if len(current) >= max_words:

            groups.append(
                current
            )

            current = []

    if current:

        groups.append(
            current
        )

    return groups


# =====================================================
# AUDIO-AWARE FALLBACK
# =====================================================

def sentence_fallback_timings(
        narration
):

    sentences = [

        sentence.strip()

        for sentence
        in re.split(
            r"(?<=[.!?])\s+",
            narration
        )

        if sentence.strip()

    ]

    parts = numbered_audio_parts()

    if (
        not sentences
        or len(parts) < len(sentences)
    ):

        return []

    result = []

    cursor = 0.0

    for index, sentence in enumerate(
        sentences
    ):

        _, audio_part = parts[index]

        part_duration = get_wav_duration(
            audio_part
        )

        if part_duration <= 0:

            return []

        start = cursor

        end = cursor + part_duration

        result.append(
            (
                start,
                end,
                tokenize(sentence)
            )
        )

        cursor = end

        cursor += silence_duration(
            index
        )

    return result


def fallback_alignment(
        words,
        audio_duration=None,
        sentence_timings=None
):

    """
    Never use the old fixed 0.35-second global clock when real audio exists.

    This fallback uses the actual generated sentence/audio durations, so it
    cannot accumulate the large forward/backward drift caused by:

        word 1 = 0.00
        word 2 = 0.35
        word 3 = 0.70
        ...

    """

    if not words:

        return []

    if (
        audio_duration is None
        or audio_duration <= 0
    ):

        duration = 0.35 * len(words)

        return [

            {

                "word": word,

                "start":
                round(
                    index * 0.35,
                    3
                ),

                "end":
                round(
                    (index + 1) * 0.35,
                    3
                )

            }

            for index, word
            in enumerate(words)

        ]

    # -------------------------------------------------
    # BEST NON-WHISPER FALLBACK:
    # REAL VOICE PART DURATIONS
    # -------------------------------------------------

    if sentence_timings:

        result = []

        for (
            start,
            end,
            sentence_words
        ) in sentence_timings:

            split = weighted_split(

                start,

                end,

                sentence_words

            )

            for word, (
                word_start,
                word_end
            ) in zip(
                sentence_words,
                split
            ):

                result.append({

                    "word": word,

                    "start":
                    round(
                        word_start,
                        3
                    ),

                    "end":
                    round(
                        max(
                            word_start + 0.005,
                            word_end
                        ),
                        3
                    )

                })

        if len(result) == len(words):

            return result

    # -------------------------------------------------
    # WHOLE-AUDIO FALLBACK
    # -------------------------------------------------

    split = weighted_split(

        0.0,

        float(audio_duration),

        words

    )

    return [

        {

            "word": word,

            "start":
            round(
                start,
                3
            ),

            "end":
            round(
                max(
                    start + 0.005,
                    end
                ),
                3
            )

        }

        for word, (
            start,
            end
        ) in zip(
            words,
            split
        )

    ]


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

    # -------------------------------------------------
    # USE THE EXACT AUDIO THAT WILL BE RENDERED
    # -------------------------------------------------

    if audio_path is None:

        default_audio = OUTPUT / "voice.wav"

        if default_audio.exists():

            audio_path = str(
                default_audio
            )

    text_words = tokenize(
        narration
    )

    aligned_words = []

    # -------------------------------------------------
    # REAL AUDIO ALIGNMENT
    # -------------------------------------------------

    if (
        audio_path
        and Path(audio_path).exists()
    ):

        audio_duration = get_wav_duration(
            audio_path
        )

        model = None

        # -------------------------------------------------
        # FIRST: SENTENCE-BY-SENTENCE REAL AUDIO ALIGNMENT
        # -------------------------------------------------

        try:

            model = load_whisper_model()

            aligned_words, ratio = align_from_sentence_parts(

                narration,

                model

            )

            # Require strong correspondence between the generated audio and
            # the narration before accepting the sentence-level alignment.
            if (
                not aligned_words
                or ratio < 0.80
                or len(aligned_words) != len(text_words)
            ):

                aligned_words = []

        except Exception as e:

            print(
                "Sentence-level Whisper alignment unavailable:",
                e
            )

            aligned_words = []

        # -------------------------------------------------
        # SECOND: ALIGN THE EXACT FINAL voice.wav
        # -------------------------------------------------

        if not aligned_words:

            try:

                if model is None:

                    model = load_whisper_model()

                transcript = transcribe_audio(

                    model,

                    audio_path,

                    expected_text=narration

                )

                aligned_words, ratio = align_transcript_to_text(

                    narration,

                    transcript,

                    audio_duration

                )

                if (
                    not aligned_words
                    or ratio < 0.70
                    or len(aligned_words) != len(text_words)
                ):

                    aligned_words = []

            except Exception as e:

                print(
                    "Whole-audio Whisper alignment unavailable:",
                    e
                )

                aligned_words = []

        # -------------------------------------------------
        # FINAL AUDIO-AWARE FALLBACK
        # -------------------------------------------------

        if not aligned_words:

            sentence_timings = sentence_fallback_timings(
                narration
            )

            aligned_words = fallback_alignment(

                text_words,

                audio_duration=audio_duration,

                sentence_timings=sentence_timings

            )

    else:

        # This path is only used when there is genuinely no generated audio.
        aligned_words = fallback_alignment(
            text_words
        )

    # -------------------------------------------------
    # GROUP WORDS
    # -------------------------------------------------

    groups = create_groups(
        aligned_words
    )

    captions = []

    # -------------------------------------------------
    # BUILD FINAL CAPTION PLAN
    # -------------------------------------------------

    for index, group in enumerate(
        groups
    ):

        styled_words = []

        for item in group:

            style = detect_style(
                item["word"]
            )

            styled_words.append({

                "word":
                str(
                    item["word"]
                ).upper(),

                "start":
                round(
                    float(
                        item["start"]
                    ),
                    3
                ),

                "end":
                round(
                    float(
                        item["end"]
                    ),
                    3
                ),

                "style":
                style["style"],

                "color":
                style["color"],

                "animation":
                style["animation"]

            })

        captions.append({

            "id":
            index + 1,

            "text":
            " ".join(
                x["word"]
                for x in styled_words
            ),

            "start":
            styled_words[0]["start"],

            "end":
            styled_words[-1]["end"],

            "words":
            styled_words,

            "font":
            "Montserrat ExtraBold",

            "position":
            "lower_center",

            "animation": {

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

    # -------------------------------------------------
    # OVERWRITE OLD / STALE CAPTION PLAN
    # -------------------------------------------------

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

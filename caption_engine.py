import json
import re
import wave
from difflib import SequenceMatcher

import numpy as np
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
# AUDIO / WORD ALIGNMENT HELPERS
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



def _normalize_token(value):

    value = str(value or "").lower().strip()

    return re.sub(
        r"[^a-z0-9']+",
        "",
        value
    )



def _weighted_time_split(start, end, words):

    count = len(words)

    if count == 0:
        return []

    start = float(start)
    end = max(start, float(end))

    weights = [
        max(
            1,
            len(_normalize_token(word))
        )
        for word in words
    ]

    total_weight = float(sum(weights)) or float(count)

    cursor = start
    result = []

    for index, weight in enumerate(weights):

        if index == count - 1:

            next_cursor = end

        else:

            next_cursor = (
                cursor
                + (end - start)
                * (weight / total_weight)
            )

        result.append(
            (
                cursor,
                next_cursor
            )
        )

        cursor = next_cursor

    return result



def _load_whisper_model():

    try:

        from faster_whisper import WhisperModel

        return WhisperModel(
            "small",
            compute_type="int8"
        )

    except Exception as e:

        print(
            "Whisper model unavailable:",
            e
        )

        return None



def _transcribe_words(model, audio_path, language="en"):

    if model is None:
        return []

    try:

        segments, _ = model.transcribe(

            str(audio_path),

            word_timestamps=True,

            language=language,

            beam_size=5,

            temperature=0,

            condition_on_previous_text=False,

            vad_filter=False

        )

        words = []

        for segment in segments:

            if not segment.words:
                continue

            for item in segment.words:

                token = str(item.word or "").strip()

                if not token:
                    continue

                words.append({
                    "word": token,
                    "start": float(item.start),
                    "end": float(item.end)
                })

        return words

    except Exception as e:

        print(
            "Whisper transcription failed:",
            e
        )

        return []



def _align_target_words(target_words, transcript_words, duration):

    if not target_words or not transcript_words or duration <= 0:
        return []

    target_norm = [
        _normalize_token(word)
        for word in target_words
    ]

    transcript = [
        item
        for item in transcript_words
        if _normalize_token(item.get("word", ""))
    ]

    transcript_norm = [
        _normalize_token(item.get("word", ""))
        for item in transcript
    ]

    matcher = SequenceMatcher(
        None,
        target_norm,
        transcript_norm,
        autojunk=False
    )

    aligned = [None] * len(target_words)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():

        if tag == "equal":

            for i, j in zip(
                range(i1, i2),
                range(j1, j2)
            ):

                start = float(transcript[j]["start"])
                end = float(transcript[j]["end"])

                aligned[i] = (
                    max(0.0, start),
                    max(start + 0.01, end)
                )

        elif tag in {"replace", "insert"} and j2 > j1 and i2 > i1:

            start = float(transcript[j1]["start"])
            end = float(transcript[j2 - 1]["end"])

            split = _weighted_time_split(
                start,
                end,
                target_words[i1:i2]
            )

            for offset, timing in enumerate(split):

                aligned[i1 + offset] = timing

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

        if run_start > 0 and aligned[run_start - 1] is not None:
            left_end = aligned[run_start - 1][1]

        right_start = float(duration)

        if (
            run_end < len(aligned)
            and aligned[run_end] is not None
        ):
            right_start = aligned[run_end][0]

        split = _weighted_time_split(
            left_end,
            max(left_end, right_start),
            target_words[run_start:run_end]
        )

        for offset, timing in enumerate(split):

            aligned[run_start + offset] = timing

    result = []
    previous_end = 0.0

    for word, timing in zip(
        target_words,
        aligned
    ):

        if timing is None:

            start = previous_end
            end = min(
                float(duration),
                start + 0.05
            )

        else:

            start, end = timing

            start = max(
                previous_end,
                min(float(duration), float(start))
            )

            end = max(
                start + 0.01,
                min(float(duration), float(end))
            )

        result.append({
            "word": word,
            "start": round(start, 3),
            "end": round(end, 3)
        })

        previous_end = end

    if result:

        result[-1]["end"] = round(
            min(float(duration), result[-1]["end"]),
            3
        )

    return result



def get_word_timestamps(
        audio_path,
        language="en"
):

    model = _load_whisper_model()

    return _transcribe_words(
        model,
        audio_path,
        language
    )



def _refine_sentence_alignment_to_audio_bounds(aligned, speech_start, speech_end):

    if not aligned:
        return []

    try:
        speech_start = float(speech_start)
        speech_end = max(speech_start + 0.01, float(speech_end))
        raw_start = float(aligned[0]["start"])
        raw_end = float(aligned[-1]["end"])
    except (TypeError, ValueError, KeyError):
        return aligned

    raw_span = raw_end - raw_start
    target_span = speech_end - speech_start

    if raw_span < 0.05 or target_span < 0.05:
        return aligned

    scale = target_span / raw_span
    refined = []
    previous_end = speech_start

    for item in aligned:
        start = speech_start + (float(item["start"]) - raw_start) * scale
        end = speech_start + (float(item["end"]) - raw_start) * scale
        start = max(previous_end, speech_start, start)
        end = min(speech_end, max(start + 0.01, end))

        refined.append({
            "word": item["word"],
            "start": round(start, 3),
            "end": round(end, 3),
        })

        previous_end = refined[-1]["end"]

    if refined:
        refined[0]["start"] = round(speech_start, 3)
        refined[-1]["end"] = round(speech_end, 3)

    return refined


def _sentence_parts_whisper_alignment(
        narration,
        audio_path,
        language="en"
):

    if not audio_path:
        return []

    audio_path = Path(audio_path)
    output_dir = audio_path.parent

    sentences = re.split(
        r'(?<=[.!?])\s+',
        str(narration or '').strip()
    )

    sentences = [
        sentence
        for sentence in sentences
        if sentence
    ]

    if not sentences:
        return []

    model = _load_whisper_model()

    if model is None:
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

        target_words = tokenize(sentence)
        if not target_words:
            return []

        transcript_words = _transcribe_words(
            model,
            part,
            language
        )

        local = _align_target_words(
            target_words,
            transcript_words,
            part_duration
        )

        if not local:
            return []

        speech_start, speech_end = _speech_bounds(part)
        local = _refine_sentence_alignment_to_audio_bounds(
            local,
            speech_start,
            speech_end,
        )

        for word in local:

            aligned.append({
                "word": word["word"],
                "start": round(
                    cursor + word["start"],
                    3
                ),
                "end": round(
                    cursor + word["end"],
                    3
                )
            })

        silence = output_dir / f"silence_{index}.wav"

        if silence.exists():
            cursor += (
                part_duration
                + _audio_duration(silence)
            )
        else:
            cursor += part_duration

    return aligned


# =====================================================
# AUDIO-SPEECH FALLBACK TIMING
# =====================================================

def _speech_bounds(path):

    try:

        with wave.open(str(path), "rb") as audio:

            sample_rate = audio.getframerate()
            channels = audio.getnchannels()
            frames = audio.readframes(audio.getnframes())

        if sample_rate <= 0:
            return 0.0, 0.0

        samples = np.frombuffer(
            frames,
            dtype=np.int16
        ).astype(np.float32)

        if channels > 1:
            samples = samples.reshape(
                -1,
                channels
            ).mean(axis=1)

        if samples.size == 0:
            return 0.0, 0.0

        samples /= 32768.0

        frame_size = max(
            1,
            int(sample_rate * 0.02)
        )
        hop = max(
            1,
            int(sample_rate * 0.01)
        )

        rms_values = []
        positions = []

        for start in range(
            0,
            max(1, len(samples) - frame_size + 1),
            hop
        ):

            frame = samples[
                start:start + frame_size
            ]

            if frame.size == 0:
                continue

            rms_values.append(
                float(
                    np.sqrt(
                        np.mean(frame * frame)
                        + 1e-12
                    )
                )
            )

            positions.append(start)

        if not rms_values:
            return 0.0, len(samples) / float(sample_rate)

        rms = np.asarray(
            rms_values,
            dtype=np.float32
        )

        reference = float(
            np.percentile(rms, 95)
        )

        threshold = max(
            0.001,
            reference * 0.08
        )

        active = rms > threshold

        # Fill tiny gaps so breaths/phoneme transitions do not split one word.
        max_gap_frames = max(
            1,
            int(round(0.08 / 0.01))
        )

        gap_start = None

        for i, value in enumerate(active):

            if value:

                if gap_start is not None:

                    gap_length = i - gap_start

                    if gap_length <= max_gap_frames:

                        active[
                            gap_start:i
                        ] = True

                    gap_start = None

            elif gap_start is None:

                gap_start = i

        active_positions = [
            i
            for i, value in enumerate(active)
            if value
        ]

        if not active_positions:
            return 0.0, len(samples) / float(sample_rate)

        first = positions[active_positions[0]]
        last_index = active_positions[-1]

        last = min(
            len(samples),
            positions[last_index] + frame_size
        )

        return (
            max(
                0.0,
                first / float(sample_rate)
            ),
            min(
                len(samples) / float(sample_rate),
                last / float(sample_rate)
            )
        )

    except Exception as e:

        print(
            "Speech-bound detection failed:",
            e
        )

        duration = _audio_duration(path)

        return 0.0, duration



def _sentence_parts_alignment(
        narration,
        audio_path=None
):

    """
    Deterministic emergency fallback based on the actual spoken portion of each
    Kokoro sentence file. Unlike the old fallback, it excludes the leading and
    trailing TTS padding and therefore does not make every caption begin early
    or finish late by the same hidden padding amount.
    """

    if not audio_path:
        return []

    audio_path = Path(audio_path)
    output_dir = audio_path.parent

    sentences = re.split(
        r'(?<=[.!?])\s+',
        str(narration or '').strip()
    )

    sentences = [
        sentence
        for sentence in sentences
        if sentence
    ]

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

        speech_start, speech_end = _speech_bounds(part)

        speech_start = min(
            max(0.0, speech_start),
            part_duration
        )

        speech_end = min(
            max(speech_start, speech_end),
            part_duration
        )

        if speech_end - speech_start < 0.05:
            speech_start = 0.0
            speech_end = part_duration

        local = _weighted_time_split(
            speech_start,
            speech_end,
            sentence_words
        )

        for word, timing in zip(
            sentence_words,
            local
        ):

            start, end = timing

            aligned.append({
                "word": word,
                "start": round(
                    cursor + start,
                    3
                ),
                "end": round(
                    cursor + max(
                        start + 0.01,
                        end
                    ),
                    3
                )
            })

        silence = output_dir / f"silence_{index}.wav"

        if silence.exists():
            cursor += (
                part_duration
                + _audio_duration(silence)
            )
        else:
            cursor += part_duration

    return aligned



def fallback_alignment(words, duration=None):

    result=[]

    time=0

    if duration is None or duration <= 0:
        duration=0.35 * len(words)

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

    for index, (word, weight) in enumerate(zip(words, weights)):

        end = (
            float(duration)
            if index == len(words) - 1
            else time + float(duration) * (weight / total_weight)
        )

        result.append({
            "word": word,
            "start": round(time, 3),
            "end": round(
                max(time + 0.01, end),
                3
            )
        })

        time = end

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

        # Align each real Kokoro sentence file independently first. This avoids
        # cumulative timestamp drift and preserves every generated sentence
        # pause exactly on the final voice clock.
        aligned_words = _sentence_parts_whisper_alignment(
            narration,
            audio_path
        )


    if not aligned_words and audio_path:

        aligned_words = _align_target_words(
            text_words,
            _transcribe_words(
                _load_whisper_model(),
                audio_path
            ),
            _audio_duration(audio_path)
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

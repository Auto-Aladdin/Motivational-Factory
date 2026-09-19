import os
import re
import subprocess
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


VOICE_OUTPUT = OUTPUT / "voice.wav"


# =====================================================
# KOKORO AI VOICE DIRECTOR
# =====================================================
#
# The narration is analyzed locally and assigned to a
# suitable Kokoro voice profile.
#
# No random male/female selection.
# No change to factory.py is required.
#
# factory.py
#     ↓
# generate_voice(narration)
#     ↓
# voice_engine.py
#     ↓
# AI Voice Director
#     ↓
# Kokoro
#

VOICE_PROFILES = {

    "stoic_male": {
        "voice": "am_adam",
        "speed": 0.86,
        "description":
            "Deep cinematic philosopher voice. Calm authority, "
            "controlled wisdom, discipline and stoic reflection.",
        "sentence_pause": 0.9,
        "dramatic_pause": 1.4
    },

    "power_male": {
        "voice": "am_michael",
        "speed": 0.92,
        "description":
            "Powerful cinematic motivational voice. Controlled intensity, "
            "determination and resilience.",
        "sentence_pause": 0.7,
        "dramatic_pause": 1.2
    },

    "warm_female": {
        "voice": "af_bella",
        "speed": 0.97,
        "description":
            "Warm documentary-style reflective voice for emotional "
            "growth and human connection.",
        "sentence_pause": 0.8,
        "dramatic_pause": 1.1
    },

    "hopeful_female": {
        "voice": "af_sarah",
        "speed": 0.95,
        "description":
            "Hopeful cinematic inspirational voice for transformation "
            "and positive change.",
        "sentence_pause": 0.8,
        "dramatic_pause": 1.2
    }

}


DEFAULT_PROFILE = "stoic_male"


SAMPLE_RATE = 24000


# =====================================================
# MOTIVATIONAL PACING
# =====================================================

PAUSE_SHORT = 0.35
PAUSE_MEDIUM = 0.75
PAUSE_LONG = 1.20


# =====================================================
# LOAD KOKORO
# =====================================================

def load_kokoro():

    try:

        from kokoro import KPipeline

        pipeline = KPipeline(
            lang_code="a"
        )

        return pipeline

    except Exception as e:

        raise Exception(
            f"Kokoro loading failed: {e}"
        )


# =====================================================
# TEXT PROCESSING
# =====================================================

def clean_text(text):

    text = text.strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def split_sentences(text):

    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )

    return [
        s.strip()
        for s in sentences
        if s.strip()
    ]


# =====================================================
# AI VOICE DIRECTOR
# =====================================================

VOICE_SIGNAL_GROUPS = {

    "stoic_male": [
        "discipline", "consistent", "consistency", "hard work",
        "routine", "focus", "focused", "control", "self control",
        "determination", "determined", "grind", "work ethic", "patience",
        "stoic", "responsibility", "restraint", "composure", "wisdom",
        "philosophy", "philosophical", "self mastery", "self-mastery"
    ],

    "power_male": [
        "sacrifice", "failure", "failed", "fail", "lost", "loss",
        "struggle", "struggled", "pain", "painful", "comeback", "quit",
        "quitting", "setback", "setbacks", "obstacle", "obstacles",
        "rejected", "rejection", "defeat", "defeated", "warrior",
        "battle", "pressure", "resistance", "fight", "fighting", "courage",
        "grit", "adversity"
    ],

    "warm_female": [
        "healing", "heal", "past", "forgive", "forgiveness", "hurt",
        "hurting", "emotional", "emotion", "growth", "growing", "journey",
        "heart", "heartbreak", "lonely", "loneliness", "memories", "regret",
        "peace", "acceptance", "letting go", "grief", "compassion",
        "self worth", "self-worth"
    ],

    "hopeful_female": [
        "change", "future", "hope", "hopeful", "believe", "believing",
        "belief", "possibility", "possibilities", "confidence", "confident",
        "opportunity", "opportunities", "vision", "goal", "goals", "success",
        "successful", "inspire", "inspiration", "inspiring", "tomorrow",
        "potential", "transformation", "transform", "new beginning", "purpose",
        "becoming", "dream", "dreams", "rebirth"
    ]
}


def _count_voice_signals(text, signals):
    lowered = str(text or "").lower()
    score = 0

    for signal in signals:
        if re.search(
            rf"\b{re.escape(signal.lower())}\b",
            lowered
        ):
            score += 1

    return score


def select_voice_profile(narration):

    """
    Select the strongest matching Kokoro voice profile from the complete
    narration instead of returning the first matching keyword bucket.
    This keeps profile selection local, deterministic, and emotion-aware.
    """

    text = narration.lower()

    scores = {
        profile: _count_voice_signals(
            text,
            signals
        )
        for profile, signals in VOICE_SIGNAL_GROUPS.items()
    }

    best_profile = max(
        scores,
        key=scores.get
    )

    if scores[best_profile] == 0:
        return DEFAULT_PROFILE

    return best_profile


# =====================================================
# EMOTIONAL PACING
# =====================================================


def apply_cinematic_performance(text, index, total, profile=DEFAULT_PROFILE):

    """
    Convert narration into a profile-specific performance style so that
    different emotional stories do not all receive the same punctuation,
    opening treatment, and dramatic cadence.
    """

    text = text.strip()

    profile_rules = {
        "stoic_male": {
            "replacements": {
                " but ": "... but ",
                " because ": "... because ",
                " however ": "... however ",
                " the truth is ": "the truth is... ",
                " remember ": "remember... "
            },
            "leading_pause": True,
            "trailing_pause": True
        },
        "power_male": {
            "replacements": {
                " but ": "...but ",
                " because ": "...because ",
                " however ": "...however ",
                " yet ": "...yet ",
                " until ": "...until "
            },
            "leading_pause": False,
            "trailing_pause": True
        },
        "warm_female": {
            "replacements": {
                " but ": "...but ",
                " because ": "...because ",
                " however ": "...however ",
                " and then ": "...and then "
            },
            "leading_pause": False,
            "trailing_pause": False
        },
        "hopeful_female": {
            "replacements": {
                " but ": "...but ",
                " because ": "...because ",
                " however ": "...however ",
                " yet ": "...yet ",
                " until ": "...until "
            },
            "leading_pause": False,
            "trailing_pause": True
        }
    }

    settings = profile_rules.get(
        profile,
        profile_rules[DEFAULT_PROFILE]
    )

    for old, new in settings["replacements"].items():
        text = text.replace(old, new)

    if index == 0 and settings["leading_pause"]:
        text = "... " + text

    if index == total - 1 and settings["trailing_pause"]:
        text = text + " ..."

    return text


def get_sentence_pause(profile, index, total):

    settings = VOICE_PROFILES.get(
        profile,
        VOICE_PROFILES[DEFAULT_PROFILE]
    )

    if index == total - 1:
        return settings.get("dramatic_pause", 1.2)

    return settings.get("sentence_pause", 0.8)


def add_emotional_pauses(sentence, profile=DEFAULT_PROFILE):

    text = sentence

    base_replacements = {
        " nobody ": "Nobody... ",
        " no one ": "No one... "
    }

    for old, new in base_replacements.items():
        text = text.replace(old, new)

    profile_replacements = {
        "stoic_male": {
            " but ": "... but ",
            " because ": "... because ",
            " however ": "... however "
        },
        "power_male": {
            " but ": "...but ",
            " because ": "...because ",
            " however ": "...however ",
            " yet ": "...yet "
        },
        "warm_female": {
            " but ": "...but ",
            " because ": "...because "
        },
        "hopeful_female": {
            " but ": "...but ",
            " because ": "...because ",
            " yet ": "...yet "
        }
    }

    for old, new in profile_replacements.get(
        profile,
        profile_replacements[DEFAULT_PROFILE]
    ).items():
        text = text.replace(old, new)

    return text


def calculate_pause(sentence):

    words = len(
        sentence.split()
    )

    if words <= 5:

        return PAUSE_SHORT

    if words >= 18:

        return PAUSE_LONG

    return PAUSE_MEDIUM


# =====================================================
# GENERATE KOKORO AUDIO PARTS
# =====================================================

def generate_parts(narration, voice_profile=None):

    pipeline = load_kokoro()

    narration = clean_text(
        narration
    )

    sentences = split_sentences(
        narration
    )

    if not sentences:

        raise Exception(
            "No valid sentences found in narration"
        )


    # -------------------------------------------------
    # Select voice ONCE for the complete narration.
    #
    # This keeps the narrator consistent throughout
    # the entire short instead of changing voices
    # sentence by sentence.
    # -------------------------------------------------

    # Respect an explicit profile/voice supplied by factory.py.
    # When omitted, preserve the original local deterministic
    # AI Voice Director behavior.
    if voice_profile:

        requested_voice = str(
            voice_profile
        ).strip().lower()

        if requested_voice in VOICE_PROFILES:

            profile = requested_voice

        else:

            profile = next(
                (
                    name
                    for name, settings
                    in VOICE_PROFILES.items()
                    if str(
                        settings.get(
                            "voice",
                            ""
                        )
                    ).strip().lower()
                    == requested_voice
                ),
                DEFAULT_PROFILE
            )

    else:

        profile = select_voice_profile(
            narration
        )

    voice_settings = VOICE_PROFILES.get(
        profile,
        VOICE_PROFILES[DEFAULT_PROFILE]
    )


    selected_voice = voice_settings["voice"]
    selected_speed = voice_settings["speed"]


    print(
        "----------------------------------------"
    )

    print(
        "AI Voice Director"
    )

    print(
        "Selected profile:",
        profile
    )

    print(
        "Kokoro voice:",
        selected_voice
    )

    print(
        "Voice speed:",
        selected_speed
    )

    print(
        "----------------------------------------"
    )


    audio_files = []


    for index, sentence in enumerate(sentences):

        processed = apply_cinematic_performance(
            add_emotional_pauses(
                sentence,
                profile
            ),
            index,
            len(sentences),
            profile
        )


        print(
            f"Generating voice part "
            f"{index + 1}/{len(sentences)}"
        )


        filename = OUTPUT / f"voice_part_{index}.wav"


        # -------------------------------------------------
        # IMPORTANT:
        #
        # speed MUST be passed into Kokoro here.
        #
        # Merely assigning:
        #
        # speed = voice_settings["speed"]
        #
        # after generation does NOT change the voice.
        # -------------------------------------------------

        generator = pipeline(

            processed,

            voice=selected_voice,

            speed=selected_speed

        )


        generated = False


        for _, _, audio in generator:

            import soundfile as sf


            sf.write(

                filename,

                audio,

                SAMPLE_RATE

            )


            generated = True

            break


        if not generated:

            raise Exception(

                f"Kokoro failed sentence "
                f"{index + 1}"

            )


        audio_files.append(
            filename
        )


        pause = get_sentence_pause(
            profile,
            index,
            len(sentences)
        )


        if pause > 0:

            silence_file = (
                OUTPUT /
                f"silence_{index}.wav"
            )


            create_silence(

                silence_file,

                pause

            )


            audio_files.append(
                silence_file
            )


    return audio_files


# =====================================================
# SILENCE GENERATOR
# =====================================================

def create_silence(path, duration):

    subprocess.run(

        [

            "ffmpeg",

            "-y",

            "-f",

            "lavfi",

            "-i",

            "anullsrc=r=24000:cl=mono",

            "-t",

            str(duration),

            str(path)

        ],

        stdout=subprocess.DEVNULL,

        stderr=subprocess.DEVNULL,

        check=True

    )


# =====================================================
# COMBINE AUDIO
# =====================================================

def combine_audio(files):

    concat = OUTPUT / "audio_concat.txt"


    with open(

        concat,

        "w",

        encoding="utf-8"

    ) as f:

        for file in files:

            absolute_path = Path(
                file
            ).resolve()


            f.write(

                f"file '{absolute_path}'\n"

            )


    command = [

        "ffmpeg",

        "-y",

        "-f",

        "concat",

        "-safe",

        "0",

        "-i",

        str(concat),

        "-ar",

        "24000",

        "-ac",

        "1",

        "-c:a",

        "pcm_s16le",

        str(VOICE_OUTPUT)

    ]


    result = subprocess.run(

        command,

        stdout=subprocess.PIPE,

        stderr=subprocess.PIPE,

        text=True

    )


    if result.returncode != 0:

        print(
            result.stderr
        )

        raise Exception(
            "Audio merge failed"
        )


    return master_voice(VOICE_OUTPUT)


# =====================================================
# AUDIO MASTERING
# =====================================================

def master_voice(input_file):

    output_file = OUTPUT / "voice_mastered.wav"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-af",
        "loudnorm=I=-16:LRA=11:TP=-1.5,acompressor=threshold=-18dB:ratio=3:attack=20:release=250,equalizer=f=3000:t=q:w=1:g=-2",
        str(output_file)
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    return output_file


# =====================================================
# FACTORY ENTRY POINT
# =====================================================

def generate_voice(narration, voice_profile=None):

    print(
        "Generating Kokoro AI-directed motivational voice..."
    )


    if not narration:

        raise Exception(
            "Empty narration received"
        )


    parts = generate_parts(
        narration,
        voice_profile=voice_profile
    )


    output = combine_audio(
        parts
    )


    print(
        "Voice generated:",
        output
    )


    return output

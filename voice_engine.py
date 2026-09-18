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

def select_voice_profile(narration):

    """
    Select the most suitable Kokoro voice profile based
    on the emotional/topic signals present in narration.

    This is intentionally local and deterministic so it
    does not add another API request or token cost.
    """

    text = narration.lower()

    # -------------------------------------------------
    # Discipline / Stoic / Hard Work
    # -------------------------------------------------

    discipline_words = [

        "discipline",
        "consistent",
        "consistency",
        "hard work",
        "sacrifice",
        "routine",
        "focus",
        "focused",
        "control",
        "self control",
        "determination",
        "determined",
        "grind",
        "work ethic",
        "patience",
        "stoic",
        "responsibility"

    ]

    if any(
        word in text
        for word in discipline_words
    ):

        return "stoic_male"


    # -------------------------------------------------
    # Failure / Resilience / Comeback
    # -------------------------------------------------

    resilience_words = [

        "failure",
        "failed",
        "fail",
        "lost",
        "loss",
        "struggle",
        "struggled",
        "pain",
        "painful",
        "comeback",
        "quit",
        "quitting",
        "setback",
        "setbacks",
        "obstacle",
        "obstacles",
        "rejected",
        "rejection",
        "defeat",
        "defeated",
        "rise again",
        "keep going",
        "keep fighting",
        "never give up"

    ]

    if any(
        word in text
        for word in resilience_words
    ):

        return "power_male"


    # -------------------------------------------------
    # Healing / Emotional Growth
    # -------------------------------------------------

    emotional_words = [

        "healing",
        "heal",
        "past",
        "forgive",
        "forgiveness",
        "hurt",
        "hurting",
        "emotional",
        "emotion",
        "change",
        "growth",
        "growing",
        "journey",
        "heart",
        "heartbreak",
        "lonely",
        "loneliness",
        "memories",
        "regret",
        "peace",
        "acceptance",
        "letting go"

    ]

    if any(
        word in text
        for word in emotional_words
    ):

        return "warm_female"


    # -------------------------------------------------
    # Dreams / Hope / Confidence
    # -------------------------------------------------

    hope_words = [

        "dream",
        "dreams",
        "future",
        "hope",
        "hopeful",
        "believe",
        "believing",
        "belief",
        "possibility",
        "possibilities",
        "confidence",
        "confident",
        "courage",
        "opportunity",
        "opportunities",
        "vision",
        "goal",
        "goals",
        "success",
        "successful",
        "inspire",
        "inspiration",
        "inspiring",
        "tomorrow",
        "potential"

    ]

    if any(
        word in text
        for word in hope_words
    ):

        return "hopeful_female"


    # -------------------------------------------------
    # Safe default
    # -------------------------------------------------

    return DEFAULT_PROFILE


# =====================================================
# EMOTIONAL PACING
# =====================================================


def apply_cinematic_performance(text, index, total):

    """
    Converts normal narration into a more deliberate
    motivational performance style.
    """

    text = text.strip()

    replacements = {
        " but ": "... but ",
        " because ": "... because ",
        " however ": "... however ",
        " the truth is ": "the truth is... ",
        " remember ": "remember... "
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Stronger opening hook treatment
    if index == 0:
        text = "... " + text

    # Final statement treatment
    if index == total - 1:
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


def add_emotional_pauses(sentence):

    text = sentence

    replacements = {

        " but ":
            "... but ",

        " because ":
            "... because ",

        " however ":
            "... however ",

        " nobody ":
            "Nobody... ",

        " no one ":
            "No one... "

    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

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

    # Respect an explicit voice supplied by factory.py.
    # When no explicit voice is supplied, preserve the existing
    # local AI voice-director behavior exactly as before.
    if voice_profile:

        requested_voice = str(voice_profile).strip().lower()

        if requested_voice in VOICE_PROFILES:
            profile = requested_voice

        else:
            profile = next(
                (
                    name
                    for name, settings in VOICE_PROFILES.items()
                    if str(settings.get("voice", "")).strip().lower()
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
            add_emotional_pauses(sentence),
            index,
            len(sentences)
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

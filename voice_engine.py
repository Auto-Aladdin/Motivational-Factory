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

    "stoic_male":
    {
        "voice": "am_adam",
        "speed": 0.90,
        "description":
            "Deep calm mentor voice. Suitable for discipline, "
            "stoicism, resilience and serious life lessons."
    },

    "power_male":
    {
        "voice": "am_michael",
        "speed": 0.95,
        "description":
            "Confident motivational coach. Suitable for ambition, "
            "challenges, failure and comeback stories."
    },

    "warm_female":
    {
        "voice": "af_bella",
        "speed": 1.00,
        "description":
            "Warm emotional storyteller. Suitable for healing, "
            "personal growth and emotional stories."
    },

    "hopeful_female":
    {
        "voice": "af_sarah",
        "speed": 0.98,
        "description":
            "Inspirational supportive voice. Suitable for dreams, "
            "hope, confidence and self-belief."
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

def generate_parts(narration):

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

        processed = add_emotional_pauses(
            sentence
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


        pause = calculate_pause(
            sentence
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


    return VOICE_OUTPUT


# =====================================================
# FACTORY ENTRY POINT
# =====================================================

def generate_voice(narration):

    print(
        "Generating Kokoro AI-directed motivational voice..."
    )


    if not narration:

        raise Exception(
            "Empty narration received"
        )


    parts = generate_parts(
        narration
    )


    output = combine_audio(
        parts
    )


    print(
        "Voice generated:",
        output
    )


    return output

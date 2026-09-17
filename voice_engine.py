import os
import re
import subprocess
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


VOICE_OUTPUT = OUTPUT / "voice.wav"


# =====================================================
# KOKORO SETTINGS
# =====================================================

VOICE = os.getenv(
    "KOKORO_VOICE",
    "af_bella"
)


SAMPLE_RATE = 24000


# Motivational pacing

PAUSE_SHORT = 0.35
PAUSE_MEDIUM = 0.75
PAUSE_LONG = 1.2



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



    for old,new in replacements.items():


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



    audio_files = []



    for index, sentence in enumerate(sentences):


        processed = add_emotional_pauses(
            sentence
        )



        print(
            f"Generating voice part {index+1}/{len(sentences)}"
        )



        filename = OUTPUT / f"voice_part_{index}.wav"



        generator = pipeline(

            processed,

            voice=VOICE

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

                f"Kokoro failed sentence {index+1}"

            )



        audio_files.append(
            filename
        )



        pause = calculate_pause(
            sentence
        )



        if pause > 0:


            silence_file = OUTPUT / f"silence_{index}.wav"



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
# COMBINE AUDIO (FIXED)
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
        "Generating Kokoro motivational voice..."
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

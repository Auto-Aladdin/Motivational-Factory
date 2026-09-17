import os
import json
import time
import subprocess
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)


VOICE_OUTPUT = OUTPUT / "voice.wav"


# =====================================================
# SETTINGS
# =====================================================

VOICE = os.getenv(
    "KOKORO_VOICE",
    "af_bella"
)


SPEED_MAP = {

    "calm":0.90,

    "normal":1.0,

    "powerful":0.92,

    "dramatic":0.85

}



# =====================================================
# LOAD KOKORO
# =====================================================

def load_kokoro():

    try:

        from kokoro import KPipeline

        return KPipeline(
            lang_code="a"
        )


    except Exception as e:

        raise Exception(
            f"Kokoro import failed: {e}"
        )





# =====================================================
# TEXT PREPROCESSING
# =====================================================

def prepare_sentence(text, emotion):


    text=text.strip()



    # Add dramatic pauses

    replacements={

        " but ":" ... but ",

        " because ":" ... because ",

        " however ":" ... however ",

        " nobody ":" nobody... "

    }


    lower=text.lower()


    for old,new in replacements.items():

        if old in lower:

            text=text.replace(
                old,
                new
            )



    # Emotional emphasis

    if emotion=="powerful":

        text = text.upper()



    return text





# =====================================================
# NORMALIZE SCRIPT
# =====================================================

def load_voice_script(data):


    if "voice_script" in data:

        return data["voice_script"]



    # Compatibility with old V5

    if "narration" in data:


        return [

            {

            "text":
            data["narration"],

            "emotion":
            "normal",

            "pause_after":
            1.0

            }

        ]



    raise Exception(
        "No narration found"
    )





# =====================================================
# GENERATE AUDIO
# =====================================================

def generate_voice_from_script(script):


    pipeline=load_kokoro()



    temp_files=[]



    for index,item in enumerate(script):


        text=item["text"]


        emotion=item.get(
            "emotion",
            "normal"
        )


        pause=item.get(
            "pause_after",
            0
        )



        processed=prepare_sentence(
            text,
            emotion
        )



        speed=SPEED_MAP.get(
            emotion,
            1.0
        )



        filename=OUTPUT / f"voice_part_{index}.wav"



        print(
            f"Generating voice part {index+1}/{len(script)}"
        )



        generator=pipeline(

            processed,

            voice=VOICE,

            speed=speed

        )



        for _,_,audio in generator:


            import soundfile as sf


            sf.write(

                filename,

                audio,

                24000

            )

            break




        temp_files.append(
            filename
        )



        # Add silence after emotional beats

        if pause > 0:

            silence_file=OUTPUT / f"silence_{index}.wav"


            subprocess.run(

                [

                "ffmpeg",

                "-y",

                "-f",

                "lavfi",

                "-i",

                f"anullsrc=r=24000:cl=mono",

                "-t",

                str(pause),

                str(silence_file)

                ],

                stdout=subprocess.DEVNULL,

                stderr=subprocess.DEVNULL

            )


            temp_files.append(
                silence_file
            )




    return combine_audio(
        temp_files
    )





# =====================================================
# JOIN AUDIO PARTS
# =====================================================

def combine_audio(files):


    concat_file=OUTPUT/"concat.txt"



    with open(
        concat_file,
        "w"
    ) as f:


        for file in files:

            f.write(

                f"file '{file}'\n"

            )



    subprocess.run(

        [

        "ffmpeg",

        "-y",

        "-f",

        "concat",

        "-safe",

        "0",

        "-i",

        str(concat_file),

        "-c",

        "copy",

        str(VOICE_OUTPUT)

        ],

        check=True

    )



    print(
        "Voice created:",
        VOICE_OUTPUT
    )



    return VOICE_OUTPUT





# =====================================================
# MAIN ENTRY USED BY FACTORY.PY
# =====================================================

def generate_voice(narration):


    print(
        "Generating Kokoro motivational voice..."
    )



    # If factory sends plain text

    if isinstance(
        narration,
        str
    ):


        script=[

            {

            "text":narration,

            "emotion":"normal",

            "pause_after":1

            }

        ]



    else:

        script=narration



    return generate_voice_from_script(
        script
    )

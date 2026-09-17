# =====================================================
# COMBINE AUDIO
# =====================================================

def combine_audio(files):


    concat = OUTPUT / "audio_concat.txt"



    with open(
        concat,
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

            str(concat),

            "-c",

            "copy",

            str(VOICE_OUTPUT)

        ],

        stdout=subprocess.DEVNULL,

        stderr=subprocess.DEVNULL,

        check=True

    )



    return VOICE_OUTPUT

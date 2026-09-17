import os
import requests
import base64
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



def generate_voice(text):

    print(
        "Generating MeloTTS voice..."
    )


    account_id = os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]

    token = os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]


    url = (

        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/myshell-ai/melotts"

    )


    payload = {

        "prompt": text

    }



    response = requests.post(

        url,

        headers={

            "Authorization":
            f"Bearer {token}",

            "Content-Type":
            "application/json"

        },

        json=payload,

        timeout=120

    )



    print(

        "Cloudflare TTS status:",
        response.status_code

    )



    if response.status_code != 200:

        print(
            response.text
        )

        raise Exception(
            "MeloTTS generation failed"
        )



    data = response.json()



    if not data.get(
        "success"
    ):

        raise Exception(
            data
        )



    result=data.get(
        "result"
    )



    if not result:

        raise Exception(
            "Empty audio result"
        )



    # Cloudflare AI audio response handling

    if isinstance(
        result,
        dict
    ):

        audio=result.get(
            "audio"
        )

    else:

        audio=result



    if not audio:

        raise Exception(
            "Audio field missing"
        )



    try:

        audio_bytes=base64.b64decode(
            audio
        )


    except Exception:


        audio_bytes=bytes(
            audio,
            "utf-8"
        )



    output_file = OUTPUT / "voiceover.mp3"



    with open(

        output_file,

        "wb"

    ) as f:

        f.write(
            audio_bytes
        )



    print(

        "Voice generated:",

        output_file

    )


    return output_file

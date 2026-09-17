import os
import requests
import base64
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



def generate_voice(text):

    print("Generating MeloTTS voice...")


    account_id = os.environ["CLOUDFLARE_ACCOUNT_ID"]
    token = os.environ["CLOUDFLARE_API_TOKEN"]


    url = (
        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/myshell-ai/melotts"
    )


    payload = {

        "text": text,

        "speaker": "EN-US-Male"

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


    response.raise_for_status()


    result=response.json()


    if "result" not in result:

        raise Exception(result)



    audio=result["result"]



    output_file=OUTPUT/"voiceover.mp3"



    # Cloudflare may return base64 audio

    if isinstance(audio,str):

        audio_bytes=base64.b64decode(audio)


    elif isinstance(audio,dict):

        if "audio" in audio:

            audio_bytes=base64.b64decode(
                audio["audio"]
            )

        else:

            raise Exception(
                "Audio data missing"
            )

    else:

        raise Exception(
            "Unknown audio format"
        )



    with open(
        output_file,
        "wb"
    ) as f:

        f.write(audio_bytes)



    print(
        "Voice created:",
        output_file
    )


    return output_file

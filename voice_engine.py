import os
import re
import json
import time
import base64
import requests
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



# =====================================
# TEXT CLEANER
# =====================================

def clean_text(text):

    text = str(text)


    # Remove markdown
    text = re.sub(
        r"[*_#`]",
        "",
        text
    )


    # Remove quotes that can break TTS
    text = text.replace(
        '"',
        ""
    )

    text = text.replace(
        "'",
        ""
    )


    # Remove unusual symbols
    text = re.sub(
        r"[^\w\s.,!?-]",
        "",
        text
    )


    # Normalize spaces
    text = " ".join(
        text.split()
    )


    return text.strip()





# =====================================
# SPLIT TEXT
# =====================================

def split_text(text, limit=450):


    sentences = re.split(
        r'(?<=[.!?])\s+',
        text
    )


    chunks=[]

    current=""


    for sentence in sentences:


        if len(current)+len(sentence) < limit:

            current += " " + sentence


        else:

            if current.strip():

                chunks.append(
                    current.strip()
                )


            current=sentence



    if current.strip():

        chunks.append(
            current.strip()
        )


    return chunks





# =====================================
# CLOUDFLARE MELOTTS
# =====================================

def call_melotts(text):


    account_id=os.environ[
        "CLOUDFLARE_ACCOUNT_ID"
    ]


    token=os.environ[
        "CLOUDFLARE_API_TOKEN"
    ]



    url=(

        f"https://api.cloudflare.com/client/v4/accounts/"
        f"{account_id}/ai/run/@cf/myshell-ai/melotts"

    )



    payload={

        "prompt": text

    }



    headers={

        "Authorization":
        f"Bearer {token}",

        "Content-Type":
        "application/json"

    }



    response=requests.post(

        url,

        headers=headers,

        json=payload,

        timeout=180

    )



    print(
        "Cloudflare TTS status:",
        response.status_code
    )



    if response.status_code != 200:


        try:

            print(
                json.dumps(
                    response.json(),
                    indent=2
                )
            )

        except:

            print(
                response.text
            )


        raise Exception(
            "Cloudflare MeloTTS failed"
        )



    data=response.json()



    if not data.get("success"):

        raise Exception(
            "MeloTTS returned unsuccessful response"
        )



    result=data.get(
        "result"
    )



    if not result:

        raise Exception(
            "No audio returned"
        )



    return result





# =====================================
# MAIN VOICE GENERATOR
# =====================================

def generate_voice(narration):


    print(
        "Generating MeloTTS voice..."
    )



    narration=clean_text(
        narration
    )



    chunks=split_text(
        narration
    )



    audio_parts=[]



    for index,chunk in enumerate(chunks):


        print(
            f"TTS chunk {index+1}/{len(chunks)}"
        )



        success=False



        for attempt in range(3):


            try:


                audio=call_melotts(
                    chunk
                )


                audio_parts.append(
                    audio
                )


                success=True

                break



            except Exception as e:


                print(
                    "TTS attempt failed:",
                    e
                )


                time.sleep(5)




        if not success:

            raise Exception(
                "MeloTTS chunk failed"
            )



    # Save response for later video pipeline

    with open(

        OUTPUT/"voice_response.json",

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            {

                "chunks":
                audio_parts

            },

            f,

            indent=2

        )



    print(
        "Voice generation complete"
    )



    return str(
        OUTPUT/"voice_response.json"
    )

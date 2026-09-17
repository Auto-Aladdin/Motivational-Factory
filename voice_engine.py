import os
import requests
import time
from pathlib import Path


OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)



def clean_text(text):

    text=text.replace(
        "\n",
        " "
    )

    text=text.replace(
        '"',
        "'"
    )

    text=" ".join(
        text.split()
    )

    return text.strip()





def generate_voice(text):


    print(
        "Generating MeloTTS voice..."
    )


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



    text=clean_text(text)



    # Split very long narration safely

    if len(text) > 700:

        text=text[:700]



    payload={

        "prompt":text

    }



    headers={

        "Authorization":
        f"Bearer {token}",

        "Content-Type":
        "application/json"

    }




    for attempt in range(3):


        try:


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



            if response.status_code == 200:


                data=response.json()



                result=data.get(
                    "result"
                )



                if result:


                    audio=result.get(
                        "audio"
                    )



                    if audio:


                        audio_file=OUTPUT/"voice.mp3"



                        with open(

                            audio_file,

                            "wb"

                        ) as f:


                            f.write(
                                bytes.fromhex(audio)
                            )



                        print(
                            "Voice generated"
                        )


                        return str(
                            audio_file
                        )



            print(
                response.text
            )


        except Exception as e:


            print(
                "TTS attempt failed:",
                e
            )



        time.sleep(5)



    raise Exception(

        "MeloTTS generation failed after retries"

    )

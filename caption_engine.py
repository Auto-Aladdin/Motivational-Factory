import json
from pathlib import Path


OUTPUT=Path("output")



def create_caption_plan(narration):


    print(
        "Creating caption plan..."
    )


    words=narration.split()



    captions=[]


    index=0


    buffer=[]



    for word in words:


        buffer.append(word)



        # Viral short caption rhythm

        if len(buffer)>=3:


            captions.append({

                "id":index,


                "text":
                " ".join(buffer),


                "highlight_words":[

                    buffer[-1]

                ],


                "style":{

                    "font":
                    "Montserrat ExtraBold",


                    "position":
                    "center",


                    "primary_color":
                    "#FFFFFF",


                    "highlight_color":
                    "#F3CE32",


                    "animation":
                    "word_pop"

                }


            })


            buffer=[]

            index+=1




    if buffer:


        captions.append({

            "id":index,

            "text":
            " ".join(buffer),

            "highlight_words":[],

            "style":{

                "font":
                "Montserrat ExtraBold",

                "position":
                "center",

                "primary_color":
                "#FFFFFF",

                "highlight_color":
                "#F3CE32",

                "animation":
                "word_pop"

            }

        })



    with open(

        OUTPUT/"caption_plan.json",

        "w",

        encoding="utf-8"

    ) as f:


        json.dump(

            captions,

            f,

            indent=2,

            ensure_ascii=False

        )


    print(
        "Caption plan complete"
    )


    return captions

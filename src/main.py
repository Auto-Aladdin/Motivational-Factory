import json
from cloudflare_ai import generate_short_plan


if __name__ == "__main__":

    result = generate_short_plan("discipline")

    with open(
        "../cache/short_plan.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            result,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("Short plan generated successfully")

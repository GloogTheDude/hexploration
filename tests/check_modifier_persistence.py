from __future__ import annotations

import sys
import requests


BASE_URL = "http://127.0.0.1:8000"


def main():
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python tests/check_modifier_persistence.py EXPEDITION_ID"
        )

    expedition_id = int(sys.argv[1])

    response = requests.get(
        f"{BASE_URL}/api/expeditions/{expedition_id}/movement-modifiers"
    )

    print("status:", response.status_code)
    print(response.json())

    if response.status_code != 200:
        raise SystemExit(1)

    data = response.json()

    print(
        "\nPersisted state:",
        f"weather={data['weather_key']},",
        f"transport={data['transport_key']}",
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import time
import requests


BASE_URL = "http://127.0.0.1:8000"


def show(label, response):
    print(f"\n=== {label} ===")
    print("status:", response.status_code)
    try:
        body = response.json()
    except Exception:
        body = response.text
    print(body)
    return body


def require(response, code):
    if response.status_code != code:
        raise SystemExit(
            f"Expected HTTP {code}, got {response.status_code}"
        )


def main():
    suffix = int(time.time())

    # Destination is forest = 1.5
    r = requests.post(f"{BASE_URL}/api/hex/1/0/FOREST")
    show("PAINT FOREST", r)
    require(r, 200)

    r = requests.post(
        f"{BASE_URL}/api/users",
        json={
            "username": f"wt_tester_{suffix}",
            "email": f"wt_tester_{suffix}@example.com",
            "password": "test-password-123",
        },
    )
    user = show("CREATE USER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns",
        json={
            "name": f"Weather transport {suffix}",
            "description": "modifier integration test",
            "epoch_name": "Day 1",
            "creator_user_id": user["id"],
        },
    )
    campaign = show("CREATE CAMPAIGN", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/characters",
        json={
            "owner_user_id": user["id"],
            "name": "Traveler",
            "race": "Human",
            "character_class": "Ranger",
            "level": 1,
            "current_game_minute": 0,
        },
    )
    character = show("CREATE CHARACTER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/maps/from-editor",
        json={
            "name": "Modifier test map",
            "version_name": "v1",
            "effective_from_game_minute": 0,
        },
    )
    snapshot = show("SNAPSHOT MAP", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/expeditions",
        json={
            "name": "Storm Riders",
            "start_game_minute": 0,
        },
    )
    expedition = show("CREATE EXPEDITION", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/characters",
        json={"character_id": character["id"]},
    )
    show("ADD CHARACTER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/position",
        json={
            "map_version_id": snapshot["map_version_id"],
            "q": 0,
            "r": 0,
        },
    )
    show("SET POSITION", r)
    require(r, 200)

    r = requests.put(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/movement-modifiers",
        json={
            "weather_key": "RAIN",
            "transport_key": "HORSE",
        },
    )
    modifiers = show("SET WEATHER + TRANSPORT", r)
    require(r, 200)

    assert modifiers["weather_key"] == "RAIN"
    assert modifiers["transport_key"] == "HORSE"

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/start"
    )
    show("START", r)
    require(r, 200)

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/move",
        json={
            "to_q": 1,
            "to_r": 0,
            "base_duration_minutes": 60,
        },
    )
    move = show("MOVE", r)
    require(r, 201)

    # 60 * 1.5 forest * 1.15 rain * 0.75 horse = 77.625 => ceil = 78
    assert move["effective_duration_minutes"] == 78

    types = [m["type"] for m in move["modifiers"]]
    assert types == ["terrain", "weather", "transport"]

    print("\nPASS: 60 × 1.5 × 1.15 × 0.75 = 78 min")


if __name__ == "__main__":
    main()

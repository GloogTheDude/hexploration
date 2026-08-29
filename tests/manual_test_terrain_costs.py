from __future__ import annotations

import time
import requests


BASE_URL = "http://127.0.0.1:8000"


def show(label: str, response: requests.Response):
    print(f"\n=== {label} ===")
    print("status:", response.status_code)

    try:
        body = response.json()
    except Exception:
        body = response.text

    print(body)
    return body


def require(response: requests.Response, expected: int):
    if response.status_code != expected:
        raise SystemExit(
            f"Expected HTTP {expected}, got {response.status_code}"
        )


def main():
    suffix = int(time.time())

    # Make the target hex FOREST before taking the persistent snapshot.
    r = requests.post(f"{BASE_URL}/api/hex/1/0/FOREST")
    show("PAINT DESTINATION FOREST", r)
    require(r, 200)

    r = requests.get(f"{BASE_URL}/api/terrains")
    terrains = show("GET TERRAINS", r)
    require(r, 200)

    forest_modifier = terrains["FOREST"]["travel_cost"]
    print("\nFOREST travel_cost:", forest_modifier)

    r = requests.post(
        f"{BASE_URL}/api/users",
        json={
            "username": f"terrain_tester_{suffix}",
            "email": f"terrain_tester_{suffix}@example.com",
            "password": "test-password-123",
        },
    )
    user = show("CREATE USER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns",
        json={
            "name": f"Terrain cost test {suffix}",
            "description": "Tests real terrain movement multiplier",
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
            "name": "Terrain Walker",
            "race": "Human",
            "character_class": "Ranger",
            "level": 1,
            "description": "Terrain cost test",
            "current_game_minute": 0,
        },
    )
    character = show("CREATE CHARACTER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/maps/from-editor",
        json={
            "name": "Terrain test map",
            "description": "Forest at 1,0",
            "version_name": "v1",
            "effective_from_game_minute": 0,
        },
    )
    snapshot = show("SNAPSHOT MAP", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/expeditions",
        json={
            "name": "Terrain Expedition",
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

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/start"
    )
    show("START EXPEDITION", r)
    require(r, 200)

    base_duration = 60

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/move",
        json={
            "to_q": 1,
            "to_r": 0,
            "base_duration_minutes": base_duration,
        },
    )
    movement = show("MOVE INTO FOREST", r)
    require(r, 201)

    expected = int(base_duration * forest_modifier)

    assert movement["modifiers"][0]["terrain_key"] == "FOREST"
    assert movement["modifiers"][0]["multiplier"] == forest_modifier
    assert movement["effective_duration_minutes"] == expected
    assert movement["arrival_game_minute"] == expected

    print(
        f"\nPASS: FOREST {base_duration} min × "
        f"{forest_modifier} = {expected} min"
    )


if __name__ == "__main__":
    main()

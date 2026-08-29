from __future__ import annotations

import requests


BASE_URL = "http://127.0.0.1:8000"


def show(label: str, response: requests.Response):
    print(f"\n=== {label} ===")
    print("status:", response.status_code)
    try:
        payload = response.json()
    except Exception:
        payload = response.text
    print(payload)
    return payload


def require(response: requests.Response, expected: int):
    if response.status_code != expected:
        raise SystemExit(
            f"Expected HTTP {expected}, got {response.status_code}"
        )


def main():
    # Use unique-ish names to avoid duplicate-user conflicts on reruns.
    import time
    suffix = int(time.time())

    r = requests.post(
        f"{BASE_URL}/api/users",
        json={
            "username": f"movement_tester_{suffix}",
            "email": f"movement_tester_{suffix}@example.com",
            "password": "test-password-123",
        },
    )
    user = show("CREATE USER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns",
        json={
            "name": f"Movement Test {suffix}",
            "description": "Movement integration test",
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
            "name": "Pathfinder",
            "race": "Human",
            "character_class": "Ranger",
            "level": 3,
            "description": "Movement test character",
            "current_game_minute": 0,
        },
    )
    character = show("CREATE CHARACTER", r)
    require(r, 201)

    # Snapshot whatever map is currently loaded in the existing editor.
    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/maps/from-editor",
        json={
            "name": "Current editor map",
            "description": "Snapshot for movement test",
            "version_name": "v1",
            "effective_from_game_minute": 0,
        },
    )
    map_snapshot = show("SNAPSHOT MAP", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign['id']}/expeditions",
        json={
            "name": "Movement Expedition",
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

    # The editor map is centered around axial (0, 0).
    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/position",
        json={
            "map_version_id": map_snapshot["map_version_id"],
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

    # (1, 0) is adjacent to (0, 0) in the current axial coordinate system.
    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/move",
        json={
            "to_q": 1,
            "to_r": 0,
            "base_duration_minutes": 60,
        },
    )
    movement = show("MOVE TO 1,0", r)
    require(r, 201)

    r = requests.get(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/movements"
    )
    movements = show("MOVEMENT HISTORY", r)
    require(r, 200)

    r = requests.get(
        f"{BASE_URL}/api/expeditions/{expedition['id']}"
    )
    expedition_after = show("EXPEDITION AFTER MOVE", r)
    require(r, 200)

    r = requests.get(
        f"{BASE_URL}/api/characters/{character['id']}"
    )
    character_after = show("CHARACTER CLOCK", r)
    require(r, 200)

    assert len(movements) == 1
    assert expedition_after["current_q"] == 1
    assert expedition_after["current_r"] == 0
    assert (
        expedition_after["current_game_minute"]
        == movement["arrival_game_minute"]
    )
    assert (
        character_after["current_game_minute"]
        == expedition_after["current_game_minute"]
    )

    print("\nALL MOVEMENT CHECKS PASSED")


if __name__ == "__main__":
    main()

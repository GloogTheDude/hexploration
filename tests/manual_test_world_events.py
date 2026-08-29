from __future__ import annotations

import math
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
        raise SystemExit(f"Expected HTTP {code}, got {response.status_code}")


def create_character(campaign_id: int, user_id: int, name: str):
    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/characters",
        json={
            "owner_user_id": user_id,
            "name": name,
            "race": "Human",
            "character_class": "Ranger",
            "level": 1,
            "current_game_minute": 0,
        },
    )
    body = show(f"CREATE CHARACTER {name}", r)
    require(r, 201)
    return body


def create_expedition(
    campaign_id: int,
    character_id: int,
    map_version_id: int,
    name: str,
    start_game_minute: int,
):
    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/expeditions",
        json={"name": name, "start_game_minute": start_game_minute},
    )
    expedition = show(f"CREATE {name}", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/characters",
        json={"character_id": character_id},
    )
    show(f"ADD CHARACTER TO {name}", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{expedition['id']}/position",
        json={"map_version_id": map_version_id, "q": 0, "r": 0},
    )
    show(f"SET POSITION {name}", r)
    require(r, 200)

    r = requests.post(f"{BASE_URL}/api/expeditions/{expedition['id']}/start")
    show(f"START {name}", r)
    require(r, 200)

    return expedition


def main():
    suffix = int(time.time())

    r = requests.post(f"{BASE_URL}/api/hex/1/0/FOREST")
    show("PAINT DESTINATION FOREST", r)
    require(r, 200)

    r = requests.post(
        f"{BASE_URL}/api/users",
        json={
            "username": f"world_event_tester_{suffix}",
            "email": f"world_event_tester_{suffix}@example.com",
            "password": "test-password-123",
        },
    )
    user = show("CREATE USER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns",
        json={
            "name": f"World Event Test {suffix}",
            "description": "Temporal world-state integration test",
            "epoch_name": "Day 1",
            "creator_user_id": user["id"],
        },
    )
    campaign = show("CREATE CAMPAIGN", r)
    require(r, 201)
    campaign_id = campaign["id"]

    early_character = create_character(campaign_id, user["id"], "Rain Walker")
    late_character = create_character(campaign_id, user["id"], "Storm Walker")

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/maps/from-editor",
        json={
            "name": "Temporal Test Map",
            "version_name": "v1",
            "effective_from_game_minute": 0,
        },
    )
    snapshot = show("SNAPSHOT MAP", r)
    require(r, 201)

    for minute, weather in [(100, "RAIN"), (300, "STORM")]:
        r = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/world-events",
            json={
                "game_minute": minute,
                "event_type": "WEATHER_CHANGED",
                "payload": {"weather_key": weather},
                "dm_note": f"Weather becomes {weather}",
            },
        )
        show(f"WEATHER @ {minute}: {weather}", r)
        require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/world-events",
        json={
            "game_minute": 200,
            "event_type": "BRIDGE_DESTROYED",
            "target_type": "BRIDGE",
            "target_id": 17,
            "payload": {"reason": "flood"},
        },
    )
    show("BRIDGE DESTROYED @ 200", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/world-events",
        json={
            "game_minute": 400,
            "event_type": "BRIDGE_REPAIRED",
            "target_type": "BRIDGE",
            "target_id": 17,
            "payload": {},
        },
    )
    show("BRIDGE REPAIRED @ 400", r)
    require(r, 201)

    expected_weather = {
        50: None,
        150: "RAIN",
        350: "STORM",
    }
    for minute, expected in expected_weather.items():
        r = requests.get(
            f"{BASE_URL}/api/campaigns/{campaign_id}/world-state",
            params={"game_minute": minute},
        )
        state = show(f"WORLD STATE @ {minute}", r)
        require(r, 200)
        assert state["weather_key"] == expected

    r = requests.get(
        f"{BASE_URL}/api/campaigns/{campaign_id}/world-state",
        params={"game_minute": 250},
    )
    state_250 = show("BRIDGE STATE @ 250", r)
    require(r, 200)
    bridge_250 = [
        event
        for event in state_250["latest_target_events"]
        if event["target_type"] == "BRIDGE" and event["target_id"] == 17
    ]
    assert bridge_250[-1]["event_type"] == "BRIDGE_DESTROYED"

    r = requests.get(
        f"{BASE_URL}/api/campaigns/{campaign_id}/world-state",
        params={"game_minute": 450},
    )
    state_450 = show("BRIDGE STATE @ 450", r)
    require(r, 200)
    bridge_450 = [
        event
        for event in state_450["latest_target_events"]
        if event["target_type"] == "BRIDGE" and event["target_id"] == 17
    ]
    assert bridge_450[-1]["event_type"] == "BRIDGE_REPAIRED"

    early = create_expedition(
        campaign_id,
        early_character["id"],
        snapshot["map_version_id"],
        "Rain Expedition",
        150,
    )
    late = create_expedition(
        campaign_id,
        late_character["id"],
        snapshot["map_version_id"],
        "Storm Expedition",
        350,
    )

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{early['id']}/move",
        json={"to_q": 1, "to_r": 0, "base_duration_minutes": 60},
    )
    early_move = show("RAIN EXPEDITION MOVE", r)
    require(r, 201)
    assert early_move["effective_duration_minutes"] == math.ceil(60 * 1.5 * 1.15)
    assert any(
        m.get("weather_key") == "RAIN"
        for m in early_move["modifiers"]
        if m["type"] == "weather"
    )

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{late['id']}/move",
        json={"to_q": 1, "to_r": 0, "base_duration_minutes": 60},
    )
    late_move = show("STORM EXPEDITION MOVE", r)
    require(r, 201)
    assert late_move["effective_duration_minutes"] == math.ceil(60 * 1.5 * 1.75)
    assert any(
        m.get("weather_key") == "STORM"
        for m in late_move["modifiers"]
        if m["type"] == "weather"
    )

    print("\nALL WORLD EVENT TEMPORAL CHECKS PASSED")
    print("Minute 150 expedition sees RAIN; minute 350 expedition sees STORM.")
    print("Bridge #17 is DESTROYED at 250 and REPAIRED at 450.")


if __name__ == "__main__":
    main()

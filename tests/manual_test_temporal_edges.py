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

    # Make the destination predictable for the movement calculation.
    r = requests.post(f"{BASE_URL}/api/hex/1/0/PLAIN")
    show("PAINT DESTINATION PLAIN", r)
    require(r, 200)

    r = requests.post(
        f"{BASE_URL}/api/users",
        json={
            "username": f"edge_tester_{suffix}",
            "email": f"edge_tester_{suffix}@example.com",
            "password": "test-password-123",
        },
    )
    user = show("CREATE USER", r)
    require(r, 201)

    r = requests.post(
        f"{BASE_URL}/api/campaigns",
        json={
            "name": f"Temporal Edge Test {suffix}",
            "description": "Bridge traversal changes with campaign time",
            "epoch_name": "Day 1",
            "creator_user_id": user["id"],
        },
    )
    campaign = show("CREATE CAMPAIGN", r)
    require(r, 201)
    campaign_id = campaign["id"]

    early_character = create_character(
        campaign_id, user["id"], "Before Repair"
    )
    late_character = create_character(
        campaign_id, user["id"], "After Repair"
    )

    r = requests.post(
        f"{BASE_URL}/api/campaigns/{campaign_id}/maps/from-editor",
        json={
            "name": "Bridge Test Map",
            "version_name": "v1",
            "effective_from_game_minute": 0,
        },
    )
    snapshot = show("SNAPSHOT MAP", r)
    require(r, 201)
    map_version_id = snapshot["map_version_id"]

    r = requests.post(
        f"{BASE_URL}/api/map-versions/{map_version_id}/edges",
        json={
            "from_q": 0,
            "from_r": 0,
            "to_q": 1,
            "to_r": 0,
            "feature_type": "BRIDGE",
            "feature_id": 17,
            "name": "North Bridge",
            "extra_data": {"river": "Test River"},
        },
    )
    edge = show("CREATE BRIDGE EDGE", r)
    require(r, 201)
    assert edge["feature_type"] == "BRIDGE"
    assert edge["feature_id"] == 17

    # Reverse coordinates must identify the same physical edge and therefore
    # be rejected as a duplicate.
    r = requests.post(
        f"{BASE_URL}/api/map-versions/{map_version_id}/edges",
        json={
            "from_q": 1,
            "from_r": 0,
            "to_q": 0,
            "to_r": 0,
            "feature_type": "BRIDGE",
            "feature_id": 99,
        },
    )
    show("REJECT REVERSED DUPLICATE EDGE", r)
    require(r, 409)

    for minute, event_type in [
        (200, "BRIDGE_DESTROYED"),
        (400, "BRIDGE_REPAIRED"),
    ]:
        r = requests.post(
            f"{BASE_URL}/api/campaigns/{campaign_id}/world-events",
            json={
                "game_minute": minute,
                "event_type": event_type,
                "target_type": "BRIDGE",
                "target_id": 17,
                "payload": {},
                "dm_note": f"Temporal traversal test: {event_type}",
            },
        )
        show(f"{event_type} @ {minute}", r)
        require(r, 201)

    early = create_expedition(
        campaign_id,
        early_character["id"],
        map_version_id,
        "Destroyed Bridge Expedition",
        250,
    )
    late = create_expedition(
        campaign_id,
        late_character["id"],
        map_version_id,
        "Repaired Bridge Expedition",
        450,
    )

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{early['id']}/move",
        json={"to_q": 1, "to_r": 0, "base_duration_minutes": 60},
    )
    blocked = show("MOVE @ 250 MUST BE BLOCKED", r)
    require(r, 409)
    detail = blocked["detail"]
    assert detail["code"] == "MOVEMENT_BLOCKED"
    assert detail["reason"] == "BRIDGE_DESTROYED"
    assert detail["target_type"] == "BRIDGE"
    assert detail["target_id"] == 17
    assert detail["edge_id"] == edge["id"]
    assert detail["game_minute"] == 250

    # A failed movement must not advance position or time.
    r = requests.get(f"{BASE_URL}/api/expeditions/{early['id']}")
    early_after = show("EARLY EXPEDITION AFTER BLOCK", r)
    require(r, 200)
    assert early_after["current_q"] == 0
    assert early_after["current_r"] == 0
    assert early_after["current_game_minute"] == 250

    r = requests.post(
        f"{BASE_URL}/api/expeditions/{late['id']}/move",
        json={"to_q": 1, "to_r": 0, "base_duration_minutes": 60},
    )
    moved = show("MOVE @ 450 MUST PASS", r)
    require(r, 201)
    assert moved["departure_game_minute"] == 450
    assert moved["arrival_game_minute"] == 510

    print("\nALL TEMPORAL EDGE CHECKS PASSED")
    print("Bridge #17 blocks movement at minute 250 and allows it at minute 450.")
    print("A blocked movement leaves expedition position/time unchanged.")


if __name__ == "__main__":
    main()

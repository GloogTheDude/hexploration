from __future__ import annotations

import time

import requests

BASE = "http://127.0.0.1:8000"
stamp = int(time.time())


def call(label: str, method: str, path: str, **kwargs):
    response = requests.request(method, BASE + path, timeout=15, **kwargs)
    print(f"\n=== {label} ===")
    print("status:", response.status_code)
    if response.content:
        print(response.json())
    return response


user = call(
    "CREATE USER",
    "POST",
    "/api/users",
    json={
        "username": f"timeline_tester_{stamp}",
        "email": f"timeline_tester_{stamp}@example.com",
        "password": "test-password-123",
    },
).json()

campaign = call(
    "CREATE CAMPAIGN",
    "POST",
    "/api/campaigns",
    json={
        "name": f"Timeline CRUD {stamp}",
        "description": "Timeline CRUD smoke test",
        "epoch_name": "Day 1",
        "creator_user_id": user["id"],
    },
).json()

campaign_id = campaign["id"]

event = call(
    "CREATE FUTURE EVENT @ DAY 3 14:30",
    "POST",
    f"/api/campaigns/{campaign_id}/world-events",
    json={
        "game_minute": 2 * 1440 + 14 * 60 + 30,
        "event_type": "BRIDGE_DESTROYED",
        "target_type": "BRIDGE",
        "target_id": 17,
        "payload": {"reason": "flood"},
        "dm_note": "Scheduled from the campaign timeline",
    },
)
assert event.status_code == 201, event.text
event = event.json()
assert event["game_minute"] == 3750

listed = call(
    "LIST TIMELINE",
    "GET",
    f"/api/campaigns/{campaign_id}/world-events",
)
assert listed.status_code == 200
assert [row["id"] for row in listed.json()] == [event["id"]]

updated = call(
    "MOVE EVENT TO DAY 4 09:00 + REPAIR",
    "PATCH",
    f"/api/world-events/{event['id']}",
    json={
        "game_minute": 3 * 1440 + 9 * 60,
        "event_type": "BRIDGE_REPAIRED",
        "payload": {},
        "dm_note": "Rescheduled and changed",
    },
)
assert updated.status_code == 200, updated.text
updated = updated.json()
assert updated["game_minute"] == 4860
assert updated["event_type"] == "BRIDGE_REPAIRED"

before = call(
    "WORLD STATE BEFORE EVENT",
    "GET",
    f"/api/campaigns/{campaign_id}/world-state?game_minute=4859",
)
assert before.status_code == 200
assert before.json()["latest_target_events"] == []

after = call(
    "WORLD STATE AFTER EVENT",
    "GET",
    f"/api/campaigns/{campaign_id}/world-state?game_minute=4860",
)
assert after.status_code == 200
assert after.json()["latest_target_events"][0]["event_type"] == "BRIDGE_REPAIRED"

deleted = call(
    "DELETE EVENT",
    "DELETE",
    f"/api/world-events/{event['id']}",
)
assert deleted.status_code == 204

final_list = call(
    "TIMELINE AFTER DELETE",
    "GET",
    f"/api/campaigns/{campaign_id}/world-events",
)
assert final_list.status_code == 200
assert final_list.json() == []

print("\nALL TIMELINE CRUD CHECKS PASSED")
print(f"UI: {BASE}/timeline.html?campaign_id={campaign_id}")

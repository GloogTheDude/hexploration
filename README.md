# Hexploration — recovered baseline + temporal WorldEvents

This archive is the consolidated recovery baseline with the temporal world-state layer added.

## What is included

- Hex map editor + terrain travel costs
- Users, campaigns, characters
- Versioned PDF character sheets
- Expeditions and movement
- Weather + transport movement modifiers
- PostgreSQL + Alembic
- **Temporal `WorldEvent` timeline and world-state resolver**

## WorldEvent model

`WorldEvent` is canonical world truth. An event belongs to a campaign and has a `game_minute`.
World state is always resolved **at a requested in-world minute**.

Example timeline:

```text
100  WEATHER_CHANGED -> RAIN
200  BRIDGE_DESTROYED -> BRIDGE #17
300  WEATHER_CHANGED -> STORM
400  BRIDGE_REPAIRED  -> BRIDGE #17
```

An expedition at minute 150 sees rain and the bridge intact. An expedition at minute 350 sees storm and the bridge destroyed.

Weather is now read from the WorldEvent timeline when movement starts. Transport remains expedition/party state.

## World event API

```text
POST /api/campaigns/{campaign_id}/world-events
GET  /api/world-events/{event_id}
GET  /api/campaigns/{campaign_id}/world-events
GET  /api/campaigns/{campaign_id}/world-state?game_minute=150
```

`WEATHER_CHANGED` expects:

```json
{
  "game_minute": 100,
  "event_type": "WEATHER_CHANGED",
  "payload": {"weather_key": "RAIN"}
}
```

Targeted world events can use `target_type` + `target_id`:

```json
{
  "game_minute": 200,
  "event_type": "BRIDGE_DESTROYED",
  "target_type": "BRIDGE",
  "target_id": 17,
  "payload": {"reason": "flood"}
}
```

The world-state endpoint returns the latest event for each target as of the requested minute, so a later `BRIDGE_REPAIRED` supersedes `BRIDGE_DESTROYED` only for expeditions whose clocks have reached it.

## Configuration

`.env` is the source of truth for both SQLAlchemy and Alembic.

Default dev configuration:

```env
DATABASE_URL=postgresql+psycopg://hexploration:hexploration@localhost:5435/hexploration
```

The Docker compose configuration uses the same database, user, password and host port.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d
alembic upgrade head
uvicorn main:app --reload
```

If you already have the existing `hexploration_postgres` container and working `.env`, keep them rather than recreating the database.

## Checks

```bash
pytest
python tests/manual_test_movement.py
python tests/manual_test_terrain_costs.py
python tests/manual_test_weather_transport.py
python tests/manual_test_world_events.py
```

`manual_test_world_events.py` verifies that two expeditions in the same campaign but at different in-world minutes resolve different weather/world states.

## Campaign Timeline UI (v0.4)

A DM-oriented timeline is available at:

```text
http://127.0.0.1:8000/timeline.html
```

or directly for a campaign:

```text
http://127.0.0.1:8000/timeline.html?campaign_id=12
```

The timeline treats `WorldEvent.game_minute` as the canonical in-world date. A future event is simply a WorldEvent whose minute is later than the expedition currently being inspected; no real-time scheduler is required.

Features:

- create events at Day / Hour / Minute;
- edit an existing event;
- delete an event;
- chronological display grouped by campaign day;
- filters by time range, event type and target;
- inspect resolved world state at any game minute;
- direct link from the map editor to the timeline.

CRUD endpoints:

```text
POST   /api/campaigns/{campaign_id}/world-events
GET    /api/world-events/{event_id}
PATCH  /api/world-events/{event_id}
DELETE /api/world-events/{event_id}
GET    /api/campaigns/{campaign_id}/world-events
GET    /api/campaigns/{campaign_id}/world-state?game_minute=...
```

No database migration is needed for this feature because it uses the existing `world_events` table.

Smoke test, with Uvicorn already running:

```bash
python tests/manual_test_timeline_crud.py
```

## v0.5 - Temporal map edges / traversal

This version adds persistent `MapEdge` rows between adjacent hexes. An edge can
represent a spatial feature such as a bridge, road segment or mountain pass and
is linked to campaign timeline events through `feature_type` + `feature_id`.

Example:

```text
MapEdge (0,0) <-> (1,0) -> BRIDGE #17
minute 200 -> BRIDGE_DESTROYED BRIDGE #17
minute 400 -> BRIDGE_REPAIRED  BRIDGE #17
```

An expedition departing at minute 250 receives HTTP 409 `MOVEMENT_BLOCKED`.
An expedition departing at minute 450 can cross the same edge.

New routes:

```text
POST   /api/map-versions/{map_version_id}/edges
GET    /api/map-versions/{map_version_id}/edges
GET    /api/map-edges/{edge_id}
DELETE /api/map-edges/{edge_id}
```

New Alembic migration:

```text
0003_map_edges
```

After copying this project over the previous version (keep your existing `.env`):

```bash
source .venv/bin/activate
alembic upgrade head
uvicorn main:app --reload
```

Then, in another terminal:

```bash
python tests/manual_test_temporal_edges.py
```

Supported traversal event pairs in this iteration:

```text
BRIDGE_DESTROYED  / BRIDGE_REPAIRED
ROAD_BLOCKED      / ROAD_REOPENED
PASSAGE_BLOCKED   / PASSAGE_OPENED
TRAVERSAL_BLOCKED / TRAVERSAL_OPENED
```

## Automated pytest coverage (v6)

The temporal gameplay rules now have real automated pytest coverage. These
service tests use an isolated in-memory SQLite database and do **not** require
Uvicorn, Docker, or the development PostgreSQL database.

Run everything with:

```bash
pytest
```

New automated coverage includes:

- temporal weather resolution at exact campaign minutes;
- destroyed/repaired traversal state;
- latest target state in `WorldState(t)`;
- canonical, non-directed `MapEdge` coordinates;
- reversed edge duplicate rejection;
- adjacency validation;
- blocked movement preserving expedition/character clocks and position;
- repaired bridge allowing traversal;
- temporal weather being included in actual movement cost.

The `manual_test_*.py` files remain useful as HTTP/PostgreSQL smoke tests, but
they are no longer the only coverage for the temporal movement rules.

## Temporal POIs (v7)
POIs are persistent map objects whose world state is resolved at a campaign `game_minute` through `WorldEvent` targeting `target_type=POI` and `target_id=<poi id>`.
Supported state events: `POI_CREATED`, `POI_STATE_CHANGED`, `POI_DAMAGED`, `POI_DESTROYED`, `POI_REBUILT`, `POI_OCCUPIED`, `POI_ABANDONED`.
This is world truth only; player discovery/knowledge remains a separate future layer.

Routes:
- `POST /api/pois`
- `GET /api/pois/{poi_id}`
- `GET /api/map-versions/{map_version_id}/pois`
- `GET /api/campaigns/{campaign_id}/pois/{poi_id}/state?game_minute=...`

Run `pytest`: expected 19 passed.

## v8 - timezone-aware UTC timestamps

All SQLAlchemy Python-side timestamp defaults now use timezone-aware UTC datetimes (`datetime.now(UTC)`) instead of deprecated `datetime.utcnow()`. This removes the Python 3.14 deprecation warnings while preserving `DateTime(timezone=True)` semantics.

Validation: `pytest` -> 19 passed, 0 warnings.

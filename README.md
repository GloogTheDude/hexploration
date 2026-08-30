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

## v9 - Discovery / character knowledge

World truth and character knowledge are now separate layers.

A POI can exist in canonical `WorldEvent` state without being known by a
character. A discovery creates an immutable `CharacterKnowledgeObservation`
snapshot at the expedition's current `game_minute`.

Example:

```text
minute 100: expedition discovers Old Watchtower -> character knows ACTIVE
minute 200: POI_DESTROYED                  -> world truth is DESTROYED
minute 250: before re-observation           -> character still knows ACTIVE
minute 250: expedition observes it again    -> character now knows DESTROYED
```

Knowledge history is preserved, so the application can answer both "what does
this character know now?" and "what did this character know at minute 150?".
Discovery is shared with every active character currently in the expedition.
For this first gameplay slice, a POI can only be discovered while the expedition
is physically on the POI's hex. Visibility/range/passive discovery can build on
this later.

Routes:

```text
POST /api/expeditions/{expedition_id}/pois/{poi_id}/discover
GET  /api/characters/{character_id}/knowledge
GET  /api/characters/{character_id}/knowledge/{target_type}/{target_id}
GET  /api/characters/{character_id}/knowledge/{target_type}/{target_id}/history
```

The two `GET` knowledge endpoints that return current state accept an optional
`as_of_game_minute` query parameter where applicable.

Database migration:

```text
0004_character_knowledge
```

Upgrade an existing v0.1.0 database with:

```bash
alembic upgrade head
```

Then run:

```bash
pytest
```

## v10 - Expedition reports -> temporal hub wiki

Discovery/knowledge remains character-level while explorers are away from the hub.
A returned expedition can now publish one report. When `publish_knowledge=true`,
the latest observation for each POI from that expedition is projected into a
campaign wiki revision.

Crucially, the wiki revision becomes available at the expedition's **in-world
return minute**, not at the wall-clock time when the HTTP request is made.

Example:

```text
minute 100 -> expedition discovers Old Watchtower = ACTIVE
minute 200 -> world truth: POI_DESTROYED
minute 300 -> expedition returns and publishes its report

hub wiki @ 299 -> no page yet
hub wiki @ 300 -> Old Watchtower = ACTIVE (the expedition's last observation)
```

A later expedition can observe the destruction and publish a second revision:

```text
minute 450 -> second expedition observes DESTROYED
minute 500 -> second expedition returns

hub wiki @ 450 -> revision 1 / ACTIVE
hub wiki @ 500 -> revision 2 / DESTROYED
```

Routes:

```text
POST /api/expeditions/{expedition_id}/report
GET  /api/expeditions/{expedition_id}/report
GET  /api/campaigns/{campaign_id}/wiki?as_of_game_minute=...
GET  /api/campaigns/{campaign_id}/wiki/pages/{page_id}?as_of_game_minute=...
```

Example report publication:

```json
{
  "title": "Northern ruins expedition",
  "content": "Returned safely after surveying the old tower.",
  "publish_knowledge": true
}
```

No Alembic migration is required for v10: the existing `expedition_reports`,
`wiki_pages`, and `wiki_revisions` tables already model this layer.

`KnowledgeRecall` is still deliberately separate and will be the next layer for
characters outside the hub.

## v0.9 - Knowledge Recall outside the hub

An active expedition can now consult a limited amount of campaign Wiki knowledge
while away from the hub without receiving information published after departure.

The temporal cutoff is always the expedition's `start_game_minute`:

```text
wiki revision @ 100 -> bridge open
expedition leaves @ 200
wiki revision @ 400 -> bridge destroyed
character recalls @ 500 -> still receives revision @ 100
```

Starter rule: each character can unlock up to **3 unique pages** per expedition.
The limit is exposed as `DEFAULT_RECALL_LIMIT_PER_CHARACTER` in
`services/recall_service.py`, so it can later become campaign-configurable without
changing the recall model.

A recalled page is shared with the whole expedition. Another character reading an
already-unlocked page does not spend one of their own recall slots. Recalled pages
remain pinned to the hub knowledge cutoff from expedition departure even if newer
Wiki revisions are published while the party is away.

Routes:

```text
GET  /api/expeditions/{expedition_id}/recall/status?character_id=...
GET  /api/expeditions/{expedition_id}/recall/search?character_id=...&q=...
POST /api/expeditions/{expedition_id}/recall
GET  /api/expeditions/{expedition_id}/recall
```

Recall request:

```json
{
  "character_id": 12,
  "page_id": 4
}
```

The existing `knowledge_recalls` table already supports this feature, so v0.9 does
not require a new Alembic migration.

## v12 - Automatic expedition visibility and POI discovery

Exploration now resolves visible POIs automatically from the expedition's
current position and in-world minute. `MapHex.visibility_score` is persisted per
map version so historical maps keep the visibility rules they were created
with.

Starter visibility model:

```text
max visible distance =
    origin hex visibility_score
    - weather penalty
    + landmark bonus
    + observer elevation bonus
    - target terrain concealment
```

Current-hex POIs are always observable. The first rule set uses weather
penalties (`RAIN`, `HEAVY_RAIN`, `STORM`, `SNOW`, `BLIZZARD`, `FOG`), a +2 range
bonus for landmarks, up to +2 for observer elevation advantage, and concealment
for terrain with a visibility score below the neutral score of 3.

This iteration deliberately does **not** perform ray-cast/occlusion through
intervening hexes yet. The scoring service is isolated so line-of-sight can be
added later without changing knowledge storage.

Routes:

```text
GET  /api/expeditions/{expedition_id}/visibility
POST /api/expeditions/{expedition_id}/visibility/observe
```

`GET` previews what is visible without changing knowledge. `POST` records the
visible POIs as `AUTO_VISIBILITY` knowledge observations. Starting a positioned
expedition, setting the position of an already-active expedition, and completing
a movement all perform this observation automatically.

Unchanged POIs are not written repeatedly while the same expedition keeps them
in sight. A changed world state, or observation by a new expedition, creates a
new immutable knowledge snapshot.

New migration:

```text
0005_map_hex_visibility
```

Run:

```bash
alembic upgrade head
pytest
```

## v13 - Hex line-of-sight and terrain occlusion

The v12 visibility range is now followed by a deterministic hex line-of-sight
check. The service traces the axial line from the expedition hex to each POI and
examines every intermediate map hex.

An intermediate hex can block sight for three reasons:

```text
MISSING_HEX          -> map geometry is absent; visibility never crosses the void
ELEVATION            -> terrain rises above the interpolated sight line
TERRAIN_CONCEALMENT  -> dense terrain adds effective obstacle height
```

Dense terrain is derived from the already-persisted `visibility_score`:

```text
opacity height = max(0, 3 - visibility_score)
```

So open terrain with score 3+ adds no LOS height, while forest-like score 2 adds
one effective level. A sufficiently elevated observer can therefore see over
some concealing terrain instead of concealment acting as an infinite wall.

The preview endpoint now exposes both `visible_pois` and `occluded_pois`.
Occluded entries include the blocker coordinate, blocker reason, interpolated
sight-line height and the complete deterministic hex path. This is intended to
make map-rule balancing/debugging inspectable from the future frontend.

No migration is required for v13; the LOS model uses existing versioned
`MapHex.elevation` and `MapHex.visibility_score` data.

Run:

```bash
pytest
```

## v14 - Fog of war and temporal map knowledge

Map geometry is now part of player knowledge instead of being implicitly known.
Every active expedition visibility pass records immutable per-character hex
observations for the cells that are actually visible through the v13 range + LOS
rules.

Fog states are intentionally simple for the first implementation:

```text
UNKNOWN -> never observed
SEEN    -> observed from another hex
VISITED -> the expedition physically occupied the hex
```

`VISITED` is monotonic: seeing the same coordinate again from a distance never
downgrades it back to `SEEN`.

Map knowledge identity is `(map_id, q, r)` rather than `MapHex.id`. This allows
new `MapVersion` rows to replace the world representation while a character
keeps the last terrain/elevation/metadata snapshot they actually observed. A
later re-observation creates a new temporal snapshot, so queries with
`as_of_game_minute` reconstruct what the character believed the map looked like
at that point in campaign time.

New routes:

```text
GET /api/characters/{character_id}/map-knowledge/{map_id}
GET /api/characters/{character_id}/map-knowledge/{map_id}/{q}/{r}
GET /api/characters/{character_id}/map-knowledge/{map_id}/{q}/{r}/history
GET /api/expeditions/{expedition_id}/map-knowledge/{map_id}
```

The existing visibility preview also exposes `visible_hexes` and
`occluded_hexes`, including LOS blocker/debug information. The observe endpoint
returns both POI knowledge observations and map-hex observations.

Automatic map knowledge updates happen in the same places as POI observation:
starting a positioned expedition, positioning an active expedition, and arriving
after movement.

New migration:

```text
0006_character_map_knowledge
```

Run:

```bash
alembic upgrade head
pytest
```

## v15 — Player fog-of-war map

A player-facing expedition map is now available at `/player.html`.

The page renders only information already present in player knowledge:

- `UNKNOWN`: not rendered as terrain; only generic adjacent movement outlines are shown.
- `SEEN`: known terrain rendered muted.
- `VISITED`: known terrain rendered with a stronger border.
- known POIs come from immutable expedition knowledge snapshots, never live world truth.
- the current expedition position is shown separately.

The consolidated API endpoint is:

```text
GET /api/expeditions/{expedition_id}/player-map
```

It intentionally does **not** enumerate canonical map hexes or undiscovered POIs. The UI supports pan, zoom, fit-to-known-map, hex inspection, selection of unknown adjacent destinations, and movement through the existing movement endpoint. A successful movement refreshes fog-of-war knowledge automatically.


## v16 — Legacy visibility bootstrap + player dashboard

- `POST /api/expeditions/{id}/player-map/bootstrap` initializes fog-of-war at the expedition current position/time only.
- `player.html` automatically bootstraps active positioned legacy expeditions that have zero map knowledge.
- The player renderer always draws the current hex and six unknown adjacent movement choices, even with zero observations.
- `/dashboard.html` lets a user select campaigns and open their participating expeditions without manually copying expedition IDs.
- No Alembic migration is required after v15.

## v17 — Player-map canvas rendering fix

The player map canvas now keeps its backing bitmap synchronized with its actual CSS size on every draw. This fixes a race where a tiny initial canvas bitmap could be stretched by the browser, making the current-position marker (`#eef7ff`) appear as a full white map. A `ResizeObserver`, first-frame layout wait, and dark canvas fallback were added. Regression checks cover the sizing contract.


## v18 — Gameplay dashboard

`/dashboard.html` now keeps Campaign → Character → Expedition context in one place and exposes Map / Wiki / Recall tabs. Active expeditions never receive the live hub wiki: the Wiki tab only renders pages already recalled by that expedition. Recall search is resolved against the temporal wiki cutoff at expedition departure and recalled pages become shared expedition knowledge. URL state (`user`, `campaign`, `character`, `expedition`) makes the dashboard directly linkable.

## v19 — DM Campaign Dashboard

The DM control center is available at `/dm.html`.

It intentionally uses a DM-only aggregate endpoint instead of exposing the campaign control surface through player APIs:

- `GET /api/users/{user_id}/dm-campaigns`
- `GET /api/campaigns/{campaign_id}/dm-dashboard?user_id=...`

The dashboard provides campaign clock/reference state, active and historical expeditions, participant lists, start/return actions, persistent map/version inventory, character clocks/statuses, recent WorldEvents, a temporal World State inspector, and an embedded full Timeline editor.

There is still no real authentication layer: `user_id` is explicit temporary context. The backend nevertheless verifies that the requested user has a `DM` membership for the campaign before returning the DM aggregate.

## v20 — DM expedition planner

The DM Control Center can now create a complete expedition without going through Swagger:

- choose the in-world departure minute;
- select one or more available ACTIVE characters;
- choose a persisted `MapVersion` and starting `(q, r)`;
- choose party transport;
- keep the expedition in `PLANNING` or start it immediately.

The dedicated DM endpoint validates the full setup before writing anything. It rejects non-DM users, characters already assigned to another open expedition, temporal backtracking for a character, a map from another campaign, a starting hex that does not exist, and a map version that is not yet effective at the expedition start minute.

Weather is intentionally **not** selected in the expedition planner: weather is campaign World Truth and continues to be resolved temporally from `WorldEvent`, while transport remains expedition state.

DM start/return buttons now use DM-authorized campaign endpoints instead of the generic expedition actions. Starting an expedition also synchronizes participating character clocks to the expedition clock.

No Alembic migration is required for v20.

## v21 — campaign creation + DM map feature workbench

The DM control center can now create campaigns directly (the current user is automatically added as DM by the existing CampaignService) and select the newly created campaign without using Swagger.

The `Cartes & versions` tab now contains a persisted-map workbench. A DM can load a MapVersion, select a hex visually, create/update a POI, create an adjacent ROAD/BRIDGE/PASSAGE/TRAVERSAL feature, and create temporal WorldEvents targeted at the selected semantic POI/feature. Feature event targeting uses `(feature_type, feature_id)`, not the internal MapEdge row id.

DM-only endpoints added:

- `GET /api/campaigns/{campaign_id}/dm-map-workbench`
- `POST /api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/pois`
- `PATCH /api/campaigns/{campaign_id}/dm-pois/{poi_id}`
- `POST /api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/edges`
- `POST /api/campaigns/{campaign_id}/dm-pois/{poi_id}/world-events`
- `POST /api/campaigns/{campaign_id}/dm-map-edges/{edge_id}/world-events`

No Alembic migration is required for v21.

## v22 — campaign bootstrap: members, characters, persisted terrain

A newly created campaign can now reach its first playable expedition without using Swagger.

The DM dashboard `Personnages` tab now lists campaign memberships and lets a DM:

- add an existing user to the campaign as PLAYER or DM;
- create a character for any campaign member;
- set the character's starting in-world minute.

DM-only endpoints added:

```text
POST /api/campaigns/{campaign_id}/dm-members?user_id=...
POST /api/campaigns/{campaign_id}/dm-characters?user_id=...
POST /api/campaigns/{campaign_id}/dm-maps/from-editor?user_id=...
```

The terrain editor is campaign-aware when opened as:

```text
/?user={dm_user_id}&campaign={campaign_id}
```

It exposes a persistence bar that snapshots the current in-memory terrain into a new persistent `WorldMap` + initial `MapVersion`, using the existing frozen terrain movement/visibility values. The save endpoint verifies DM membership server-side. After persistence the new map becomes available in the DM dashboard Map Workbench and expedition planner.

This version intentionally creates a *new* persistent map from the editor. Creating a later terrain `MapVersion` for an existing map is deferred until semantic POI/feature identity across versions is formalized, so temporal WorldEvent targets cannot silently break when rows are copied between versions.

No Alembic migration is required for v22.

## v23 — semantic feature identities + real MapVersion workflow

MapVersion rows are now allowed to evolve without breaking temporal WorldEvent targets.

- New `map_features` registry stores campaign-scoped semantic identities.
- `PointOfInterest.feature_id` is now the stable POI identity used by `WorldEvent.target_id`, character knowledge, wiki projection and future versions.
- Existing POI rows are backfilled with `feature_id = old poi.id`, so historical `POI_*` events remain valid after migration.
- Existing `MapEdge.feature_id` values are registered as semantic feature identities and preserved across versions.
- Creating a new map version from the terrain editor copies POIs and edges to new concrete rows while preserving their semantic feature ids.
- Loading a persisted version into the editor rehydrates its frozen terrain movement/visibility/elevation values rather than silently replacing them with current defaults.

DM workflow:

1. `Cartes & versions` → click **Éditer → nouvelle version** on a persisted version.
2. The editor loads that version from PostgreSQL.
3. Paint the terrain.
4. Choose the effective game minute and click **Créer la nouvelle version**.
5. The new `MapVersion` receives `parent_version_id`, a new version number and copied POI/edge rows with unchanged semantic identities.

New DM endpoints:

- `POST /api/campaigns/{campaign_id}/dm-map-versions/{map_version_id}/load-editor?user_id=...`
- `POST /api/campaigns/{campaign_id}/dm-maps/{map_id}/versions/from-editor?user_id=...`

Database migration:

```bash
alembic upgrade head
```

New head: `0007_semantic_map_features`.


## v24 — Campaign invitations and player-owned character creation

Campaign entry now follows an explicit invitation flow: a DM invites an existing user, the invitation remains `PENDING`, and no membership exists until the invited user accepts. Acceptance creates a `PLAYER` membership; refusal creates none. The player dashboard exposes pending invitations and Accept/Refuse actions. Once accepted, the player can select the campaign and create their own character. The DM dashboard no longer creates player characters. User-ID invitation is intentionally retained for the current test phase; name/email lookup is deferred.

Migration: `0008_campaign_invitations`.

## v25 — Campaign onboarding UX

- Player character creation now opens in a responsive modal instead of squeezing the form into the sidebar.
- Players can permanently delete their own characters only while they have no expedition history.
- Historical characters are preserved and can be retired (`ACTIVE -> RETIRED`) instead of being physically deleted.
- Player invitations refresh automatically while the dashboard is visible and also expose a manual refresh button.
- The DM campaign member panel now lists sent invitations and their `PENDING`, `ACCEPTED`, or `REFUSED` state.
- Refused invitations can be sent again directly from the DM dashboard.
- No Alembic migration is required after v24; database head remains `0008_campaign_invitations`.

Validation: `pytest` -> 110 passed.

## v26 - Character sheet PDF workspace

Player characters now have a PDF sheet workspace in `/dashboard.html`.

- `Fiche PDF` opens the current sheet inline and exposes version history.
- A player may upload a PDF; each upload creates a new immutable `CharacterSheetVersion` and makes it current.
- The sheet is owner-scoped through the temporary `user_id` auth context used by the current MVP.
- Immediately after player character creation, the dashboard asks the backend to create a personal version 1 from the official D&D 5e fillable character sheet and opens it.
- The official PDF is **not bundled in the repository**. On first use the backend downloads it from Wizards of the Coast and caches it locally at `storage/templates/5E_CharacterSheet_Fillable.pdf`.
- For offline/self-hosted use, download the template yourself and set `CHARACTER_SHEET_TEMPLATE_PATH` in `.env`.
- Browser PDF viewers can fill the AcroForm, but browsers do not expose those unsaved edits back to Hexploration. Use the viewer's Save/Download action, then upload the resulting PDF in the same modal. The uploaded copy becomes the next persisted version.

Relevant routes:

```text
POST /api/characters/{character_id}/sheets/template?user_id=...
POST /api/characters/{character_id}/sheets?user_id=...
GET  /api/characters/{character_id}/sheets?user_id=...
GET  /api/characters/{character_id}/sheets/current?user_id=...
GET  /api/characters/{character_id}/sheets/current/pdf?user_id=...
GET  /api/characters/{character_id}/sheets/{version}/pdf?user_id=...
```

No Alembic migration is required for v26; the existing `character_sheet_versions` table already models sheet history.

## v27 — Fiche personnage native + export PDF

La fiche PDF n'est plus l'éditeur principal. Les données de personnage sont maintenant éditées directement dans Hexploration et versionnées en base de données.

- `CharacterSheetDataVersion` conserve un snapshot JSON immuable à chaque clic sur **Enregistrer une version**.
- L'ouverture de la fiche initialise automatiquement la version 1 depuis les informations déjà présentes sur `Character` (nom, race, classe, niveau, description et joueur).
- Le formulaire couvre identité, six caractéristiques, combat, équipement, personnalité et biographie. Les modificateurs de caractéristiques sont calculés automatiquement dans l'UI et lors de l'export.
- Les champs d'identité sauvegardés dans la fiche resynchronisent la carte `Character` afin d'éviter deux sources contradictoires pour nom/race/classe/niveau.
- Une ancienne version peut être rechargée dans le formulaire; l'enregistrer crée une nouvelle version au lieu de modifier l'historique.
- **Exporter PDF** génère le PDF à la demande depuis n'importe quelle version DB. Le template officiel remplissable reste seulement un format de sortie.
- Le template est chargé depuis `CHARACTER_SHEET_TEMPLATE_PATH` s'il est configuré; sinon le backend essaie de mettre en cache la fiche officielle Wizards au premier export.
- Les anciens endpoints d'upload PDF v26 restent présents pour compatibilité, mais ne sont plus exposés dans l'interface principale.

Migration : `0009_character_sheet_data`.

Routes principales :

```text
POST /api/characters/{character_id}/sheet-data/initialize?user_id=...
POST /api/characters/{character_id}/sheet-data?user_id=...
GET  /api/characters/{character_id}/sheet-data?user_id=...
GET  /api/characters/{character_id}/sheet-data/current?user_id=...
GET  /api/characters/{character_id}/sheet-data/current/pdf?user_id=...
GET  /api/characters/{character_id}/sheet-data/{version}/pdf?user_id=...
```

### v29.1 editor hotfix
The map editor ES module graph is cache-busted consistently (`?v=291`) so browsers cannot mix the new editor entrypoint with stale pre-v29 dependencies. This fixes the blank canvas / empty terrain palette / dead controls symptom after upgrading from an older version.

## Large-map editor performance (v29.5)

The terrain editor supports sparse maps up to 10,000×10,000 logical hexes (100,000,000 logical cells) without materializing the full grid.
Painting is applied immediately in the browser and synchronized to the backend in short deduplicated batches. Canvas redraws are scheduled with `requestAnimationFrame`, rectangular maps are viewport-culled, and very distant zoom levels use a coarse preview rather than drawing every polygon.

Map persistence no longer flushes one SQLAlchemy row at a time. New versions are inserted in batches, while updates to a loaded unused version write only the dirty painted coordinates. Large JSON map responses are gzip-compressed by the ASGI app.

Large maps use sparse storage: only modified/supporting cells are materialized, while the untouched background remains implicit.

## Large-map storage (v30)

New map versions use sparse terrain storage. A map can be up to `10,000 x 10,000`
logical hexes without allocating 100 million Python objects or database rows.
`MapVersion.default_terrain_key` defines the implicit terrain (currently `SEA`)
and `MapHex` rows materialize only edited/supporting cells. The editor and DM
workbench render only the visible viewport and use a coarse overview at world
zoom. Legacy dense map versions remain loadable.

After upgrading an existing database run:

```bash
alembic upgrade head
```


### v30.1 — navigation éditeur

- Les cartes s'ouvrent désormais à **100 % (1 pixel monde = 1 pixel CSS)** au lieu d'être automatiquement ajustées au viewport.
- Le bouton **Ajuster** conserve la vue complète de la carte à la demande.
- Maintenir **Espace** active temporairement le déplacement du viewport, même si le pinceau est actif ; relâcher Espace restaure immédiatement le pinceau.
- Le raccourci Espace n'intercepte pas la saisie dans les champs de formulaire.


### v30.2 — brush hot-path optimization

Brush strokes are rendered locally per touched hex instead of forcing a full viewport redraw on every pointer event. Server synchronization is deferred until the stroke ends (with a safety batch threshold), making brush latency independent of total map dimensions in normal editing.

## v0.31 editor/workbench feature tools

- Terrain editor: stroke-level Ctrl+Z / Ctrl+Shift+Z with exact sparse-map server synchronization.
- DM POI workbench: Ctrl+Z / Ctrl+Shift+Z for POI create/update operations.
- Ordered multi-selection becomes linear-feature waypoints: ROAD and RIVER interpolate every hex between selected waypoints.
- BRIDGE, PASSAGE and TRAVERSAL remain two-adjacent-hex features.
- ROAD and RIVER may share the same physical corridor while keeping separate semantic identities and temporal state.
- RIVER segments preserve path/flow direction in `extra_data.path_from/path_to`.
- Area features (`LAKE`, `INLAND_SEA`, `WETLAND`, `REGION`) persist selected hex sets independently from terrain.
- Migration `0011_linear_area_features` adds ordered edge segments, overlapping semantic edge support and persisted map areas.

## v0.33 — World Editor UX pass

The semantic World Editor now uses an editor-style workflow: compact tool rail, large map canvas, contextual inspector and an optional object browser. POIs, linear features and areas can be selected directly on the map. Roads/rivers are rendered as ordered polylines, shared river/road corridors keep a stable lateral offset, water areas receive a stronger continuous fill and shoreline, and POI marker borders distinguish landmarks from hidden/local POIs. Safe hard-delete actions are available for POIs, linear features and areas; deletion is refused when timeline events or player knowledge already reference the semantic feature.

### River networks (v34)

Rivers now form a directed hydrographic network. A new river stops at the first
existing river it reaches and stores a stable downstream river relationship on
`MapFeature`; downstream geometry is not duplicated. Short outlet completion
can target an existing river as well as SEA/LAKE/INLAND_SEA. The World Editor
renders river corridors as one de-duplicated network with explicit confluence
joins. Deleting a downstream river is blocked while tributaries still reference
it. Migration: `0012_river_networks`.

## v35 — shoreline outlets and linear feature merge

- River rendering stops at the land/water shoreline for SEA, LAKE and INLAND_SEA outlets instead of drawing to the center of the water hex.
- ROAD and RIVER features can be multi-selected with Ctrl/Cmd+click and merged when they form one continuous chain.
- The first selected feature keeps its stable semantic identity; unsafe absorbed identities with history or geometry in another map version are rejected.
- Linear selection uses a white halo while preserving the feature's own route/river color.
- POIs use a yellow fill, white outline when hidden/not landmark-visible, and dark outline when visible at distance.


## v36 — World Editor semantic undo and hex cleanup

- ROAD merge now accepts any connected network, including T-junctions, branches and cycles.
- Merged road networks render as graph segments instead of an invented single polyline.
- Normal clicks on LAKE/area cells select the hex; Alt+click explicitly selects the area object.
- Shift+click forces hex selection beneath POIs/linear features.
- Delete on a selected hex removes semantic content on that cell without changing terrain; area membership removes only that cell and linear networks are split when needed.
- Ctrl+Z / Ctrl+Shift+Z now use transactional World Editor snapshots covering POIs, linear features, areas and their world events.
- No database migration is required beyond 0012_river_networks.

## v41.1 World Editor hotfix

- Stabilise la toolbar Version / Minute / Sauvegarde / Undo / Redo.
- Corrige les listeners Sauvegarder et Afficher qui avaient été accidentellement attachés dans undoWorld().
- Rend la timeline WorldEvent explicitement visible avec états chargement/vide/erreur et tri chronologique.
- Initialise la minute globale depuis la campagne.

## v42 — temporal POI state + readable campaign calendar

- The World Editor keeps canonical `game_minute` integers in the API/database, but exposes a readable fixed campaign calendar: **year / month / day / hour / minute**.
- Calendar convention: 12 months/year, 30 days/month, 24 hours/day. Year starts at 0; month/day start at 1.
- POI event forms are semantic instead of JSON-first. `POI_STATE_CHANGED` exposes a state selector and every POI event can explicitly keep/change `visible_at_distance`.
- `POI_VISIBILITY_CHANGED` changes long-distance visibility without overwriting the physical POI state.
- POI temporal state is folded across the complete event history so state and visibility remain independent properties.
- World Editor preview resolves each POI at the selected campaign date. POI borders and object-browser metadata reflect temporal visibility; destroyed POIs receive a destroyed marker.
- Visibility scans now use temporal `visible_at_distance`, so a lit living settlement may be visible from farther away and stop receiving the landmark range bonus after a destruction/visibility event.
- Raw payload JSON remains available under an **Advanced** disclosure for uncommon/custom event data.


## v44.1 — World Editor UI stabilization
- Header split into two rows for readable version/time/history controls.
- Inspector no longer horizontally overflows on event date forms.
- POI WorldEvent editing now has explicit progress/error feedback and deterministic timeline refresh after PATCH.
- Cache bust updated to 451.

# Hexploration MVP Backlog

## Rules

Tasks are processed by priority.

Allowed states:

- `TODO`
- `IN_PROGRESS`
- `DONE`
- `BLOCKED`
- `NEEDS_POSTGRES_VALIDATION`
- `NEEDS_USER_DECISION`

The agent must follow `AGENTS.md`.

Do not add new product features while processing this backlog.

---

# Milestone 1 — Core Workflow Stabilization

Goal:

Validate and stabilize the complete MVP gameplay foundation before authentication work begins.

Target workflow:

    campaign
      ↓
    character
      ↓
    world/map
      ↓
    expedition
      ↓
    movement
      ↓
    discovery / fog of war
      ↓
    persisted state

---

## P0 — Database reproducibility

### DB-001 — Repair reproducible initial Alembic migration

Status: `DONE`

Acceptance criteria:

- `0001_initial_schema` is deterministic;
- it does not depend on current SQLAlchemy metadata;
- fresh PostgreSQL database upgrades from base to head;
- final revision is `0016_dm_ping`;
- resulting schema matches development schema;
- complete SQLite suite passes;
- complete PostgreSQL suite passes.

Validation:

- SQLite: 243 passed
- PostgreSQL: 243 passed
- PostgreSQL 18 migration base → head: PASS
- final schema comparison: PASS

---

## P0 — Campaign workflow

### CORE-001 — Audit campaign creation workflow

Status: `DONE`

Result:

- campaign creation persists the campaign and creator DM membership;
- unknown creators are rejected;
- required campaign text fields now reject whitespace-only values;
- focused and complete SQLite tests pass (`247 passed`).

Verify the complete campaign creation path from HTTP request to persisted state.

Acceptance criteria:

- valid campaign creation succeeds;
- required fields are validated;
- invalid requests return appropriate errors;
- campaign is persisted correctly;
- creator/DM relationship is correct;
- relevant tests cover successful and invalid creation;
- no unrelated refactor.

---

### CORE-002 — Audit character creation workflow

Status: `DONE`

Result:

- valid characters persist with the campaign owner and expected defaults;
- invalid campaigns, owners, and non-members are rejected;
- whitespace-only names are rejected;
- focused and complete SQLite tests pass (`251 passed`).

Verify character creation inside a campaign.

Acceptance criteria:

- valid character creation succeeds;
- campaign relationship is correct;
- ownership/player relationship is correct;
- invalid campaign/user references are rejected;
- required character fields are validated;
- relevant tests exist.

---

## P0 — World creation

### WORLD-001 — Audit map/world creation workflow

Status: `DONE`

Result:

- maps and initial versions persist with the campaign association;
- logical dimensions, sparse default terrain, and version zero-time behavior are covered;
- unknown campaigns and blank map names are rejected;
- focused and complete SQLite tests pass (`254 passed`).

Verify that a campaign can create and persist its world/map.

Acceptance criteria:

- map creation succeeds;
- initial map version is valid;
- campaign ownership is correct;
- required defaults are correct;
- invalid state is rejected;
- relevant tests exist.

---

### WORLD-002 — Audit map version lifecycle

Status: `DONE`

Result:

- version/map association and semantic identity preservation are covered;
- sparse maps and historical version immutability are covered;
- updates cannot move a version to or before its parent effective time;
- negative initial effective times are rejected;
- focused and complete SQLite tests pass (`256 passed`).

Verify map-version creation and historical behavior.

Acceptance criteria:

- map versions are correctly associated with their map;
- temporal/version ordering remains valid;
- sparse-map behavior remains correct;
- existing historical state is not mutated unexpectedly;
- relevant tests exist.

---

## P0 — Expedition workflow

### EXP-001 — Audit expedition creation

Status: `DONE`

Result:

- expedition creation persists the campaign and planning state correctly;
- the DM planner validates members, active characters, map version, hub, and time before persistence;
- invalid campaigns and blank names are rejected;
- focused and complete SQLite tests pass (`259 passed`).

Verify expedition creation from a valid campaign/world state.

Acceptance criteria:

- expedition can be created;
- characters can be assigned correctly;
- starting location is valid;
- starting campaign/game time is valid;
- invalid participants or locations are rejected;
- relevant tests exist.

---

### EXP-002 — Audit expedition movement

Status: `DONE`

Result:

- valid movement persists position, elapsed time, costs, and participant clocks;
- temporal weather and edge blocking are resolved at departure time;
- invalid destinations and non-positive durations are rejected;
- undo restores the prior state;
- focused and complete SQLite tests pass (`261 passed`).

Verify the complete movement workflow.

Acceptance criteria:

- valid movement changes expedition position;
- game time advances correctly;
- terrain/travel rules are respected;
- invalid movement is rejected;
- persisted state remains consistent;
- relevant tests exist.

---

### EXP-003 — Audit expedition temporal state

Status: `DONE`

Result:

- expedition clocks and world events resolve at the requested game minute;
- historical POI/map knowledge is preserved across later world changes;
- focused temporal tests and the complete SQLite suite pass (`261 passed`);
- no code change was necessary.

Verify that expedition state is resolved according to world/game time.

Acceptance criteria:

- expedition time is persisted correctly;
- temporal world state is resolved at the appropriate game minute;
- historical state is not overwritten by future state;
- relevant regression tests exist.

---

## P0 — Discovery and fog of war

### FOG-001 — Audit hex discovery

Status: `DONE`

Result:

- origin and visible hexes are persisted as `VISITED`/`SEEN` knowledge;
- occluded and unrelated hexes remain unknown;
- discovery is character-specific and durable;
- focused and complete SQLite tests pass (`261 passed`);
- no code change was necessary.

Verify discovery behavior when an expedition explores the map.

Acceptance criteria:

- discovered hexes become known appropriately;
- discovery persists;
- unrelated hexes remain undiscovered;
- discovery respects campaign/character context;
- relevant tests exist.

---

### FOG-002 — Audit player map visibility

Status: `DONE`

Result:

- player map payloads are built from character knowledge, not canonical map data;
- unknown hexes, POIs, edges, and area geometry are filtered server-side;
- endpoint access now derives from the authenticated session;
- campaign DMs and participating players receive the same filtered payload;
- non-participating players receive `403`, outside-campaign users receive
  `404`, and anonymous requests receive `401`;
- DM ping fields are excluded from the player-map JSON;
- focused authorization tests and the complete SQLite suite pass (`274 passed`).

Verify that player-facing map data contains only information the player is allowed to know.

Acceptance criteria:

- undiscovered information is not exposed;
- discovered terrain is exposed correctly;
- POI knowledge respects discovery rules;
- DM-only information is not leaked;
- server-side behavior enforces visibility;
- negative tests exist.

---

### FOG-003 — Audit character knowledge persistence

Status: `DONE`

Result:

- character knowledge is persisted as immutable time-stamped observations;
- future world changes do not rewrite earlier snapshots;
- knowledge remains character-specific and is shared only with active expedition participants;
- focused and complete SQLite tests pass (`261 passed`);
- no code change was necessary.

Verify immutable/historical character knowledge behavior.

Acceptance criteria:

- knowledge observations persist correctly;
- later world changes do not rewrite historical observations;
- character-specific knowledge remains isolated;
- relevant tests exist.

---

# Milestone 2 — Authentication and Authorization

Do not begin this milestone until Milestone 1 has no unresolved P0 blockers unless explicitly instructed.

### AUTH-001 — Audit current identity model

Status: `DONE`

Determine current user identity assumptions and identify endpoints trusting client-supplied identity.

This is an analysis task.

Result:

- no server-side authentication dependency or current-user resolver exists;
- the existing User model already stores `password_hash`, and UserService
  hashes passwords with `pwdlib`/Argon2 recommended settings;
- campaign roles are contextual `CampaignMembership` rows (`PLAYER`/`DM`),
  not a global user flag;
- routes and frontend flows currently trust query/body/path `user_id`
  values, including DM operations and player-owned resources;
- FOG-002 player-map reads currently receive only `expedition_id` and have
  no requester identity or access check;
- implementation must wait for the authentication/session design below.

Do not implement authentication during this task.

---

### AUTH-002 — Design MVP authentication flow

Status: `DONE`

Requires completion of AUTH-001.

May become `NEEDS_USER_DECISION` if multiple materially different authentication strategies are appropriate.

Result:

- recommended design: Argon2id password verification plus a database-backed
  opaque session cookie, with only a cryptographic token hash persisted;
- approved decisions: public registration through the existing
  `POST /api/users` workflow, contextual expedition access, filtered DM
  player-map responses, 401/403/404 resource behavior, safe handling of
  invalid password hashes, fixed 30-day sessions, and opaque database-backed
  sessions;
- authentication foundation implementation is authorized; broad route
  authorization remains a separate phase.

---

### AUTH-003 — Implement password security

Status: `DONE`

Existing `pwdlib`/Argon2 password hashing and safe invalid-hash handling were
validated during the authentication foundation.

---

### AUTH-004A — Implement authentication foundation

Status: `DONE`

Phase 1 foundation implemented:

- `UserSession` stores only a SHA-256 token hash;
- sessions expire after a fixed 30 days and support multiple simultaneous
  sessions;
- logout deletes the session and user deletion cascades sessions;
- `/auth/login`, `/auth/logout`, and `/auth/me` are available;
- `get_current_user()` rejects anonymous, expired, deleted, and invalid
  sessions with `401`;
- cookie-authenticated unsafe requests receive same-origin Origin/Referer
  protection;
- broad campaign, expedition, and FOG-002 authorization is intentionally
  not included in this phase;
- SQLite focused tests and the complete suite pass (`270 passed`);
- PostgreSQL runtime validation succeeded (`270 passed`).

---

### AUTH-004 — Implement authentication

Status: `DONE`

Superseded by the validated AUTH-004A foundation.

---

### AUTH-005 — Protect DM operations

Status: `DONE`

Campaign-scoped DM operations now derive caller identity from the
authenticated session and require contextual `CampaignMembership.role == DM`.
PostgreSQL regression validation succeeded as part of the Phase 2 suite
(`274 passed`).

---

### AUTH-006 — Protect player resources

Status: `DONE`

Campaign, character, expedition, knowledge, visibility, recall, wiki and
player-map resources now require the appropriate authenticated membership,
ownership or expedition participation. PostgreSQL regression validation
succeeded (`274 passed`).

---

### AUTH-007 — Add authorization regression suite

Status: `DONE`

Regression tests cover DM/PLAYER/non-member expedition access, caller
identity impersonation, cross-campaign hiding and filtered player-map output.
The complete SQLite suite passes (`274 passed`).

The legacy global editor endpoints (`/api/map`, `/api/hex/*`,
`/api/newmap/*`) were identified for the separate MAP-001 ownership cleanup.

### AUTH-008 — Frontend authentication integration

Status: `DONE`

Add the smallest vanilla JavaScript authentication gate for the existing
frontend: `/auth/me` bootstrap, login, logout, centralized `401` handling,
and server-derived current-user state. Do not persist session tokens or add
database changes.

Result:

- all frontend entry points now bootstrap through `/auth/me` before loading
  protected application data;
- login and logout use the existing cookie-session endpoints;
- expired sessions return the UI to login through one shared `401` handler;
- dashboard and DM caller identity comes from `/auth/me`, not a URL or input;
- player/DM target selectors remain domain data where applicable;
- focused frontend tests pass (`30 passed`);
- complete SQLite suite passes (`280 passed`);
- PostgreSQL regression validation passes (`280 passed in 106.70s`).

### AUTH-009 — Registration UI

Status: `DONE`

Public registration is integrated into the existing authentication gate.

Result:

- login and registration are switchable in the same anonymous UI;
- registration sends only `username`, `email` and `password` to
  `POST /api/users`;
- successful registration automatically reuses `/auth/login` and then
  `/auth/me` for the authenticated identity;
- failed automatic login reports that the account was created and returns to
  login without pretending registration failed;
- duplicate identities return a stable `409` response;
- unknown privilege fields are rejected by the public user DTO;
- password fields are cleared after registration and no password/session
  state is persisted in browser storage;
- focused tests pass (`22 passed`);
- complete SQLite suite passes (`286 passed`);
- PostgreSQL regression validation passes (`286 passed in 107.54s`).

---

# Milestone 3 — UX Stabilization

Do not begin unless explicitly instructed or earlier milestones are complete.

### UX-001 — Audit frontend error handling

Status: `DONE`

Result: The primary frontend pages surface backend `detail` errors and handle failed API responses consistently. Covered by `tests/test_mvp_ux_assets.py`; no code change was necessary.

### UX-002 — Add missing loading states

Status: `DONE`

Result: The application, dashboard, DM, world and player workflows expose loading feedback before data and save operations complete. Covered by `tests/test_mvp_ux_assets.py`; no code change was necessary.

### UX-003 — Add save/success feedback

Status: `DONE`

Result: Existing editor and management workflows expose save/progress feedback, including success feedback where applicable. Covered by `tests/test_mvp_ux_assets.py`; no code change was necessary.

### UX-004 — Audit navigation consistency

Status: `DONE`

Result: The primary frontend pages retain cross-area navigation links for the existing dashboard, DM, player, timeline and world workflows. Covered by `tests/test_mvp_ux_assets.py`; no code change was necessary.

---

# Phase 5 — Map/editor ownership

### MAP-001 — Resolve legacy global editor ownership

Status: `DONE`

Result:

- The persisted campaign/editor routes are scoped and authorized through `MapVersion → Map → Campaign`; POIs, edges and areas derive ownership through their map version, and player-map access remains separate and filtered.
- The frontend editor now creates, loads, paints, updates and clones persistent campaign map versions through the DM workbench routes. It no longer calls the global `/api/map`, `/api/hex/*` or `/api/newmap/*` endpoints.
- The global in-memory editor routes and their movement integration were removed. The terrain catalog remains available through the dedicated `/api/terrains` route.
- No schema changes were required. Focused migration tests pass (`40 passed`); the complete SQLite suite passes (`288 passed`), and fresh PostgreSQL validation passes (`288 passed in 109.31s`).

---

### UX-005 — Restore world editor campaign navigation

Status: `DONE`

The World Editor exposes an explicit campaign/dashboard link that preserves the `campaign` context without using a client-supplied `user_id` as identity. The link remains visible in the compact header layout, and the campaign name is displayed when available from the authenticated DM dashboard response. Covered by `tests/test_world_editor_frontend_assets.py`.

This change is frontend-only and requires no additional PostgreSQL validation.


---

# Milestone 4 — Deployment

### DEPLOY-001 — Reproducible production setup

Status: `TODO`

### DEPLOY-002 — Database backup procedure

Status: `TODO`

### DEPLOY-003 — Database restore procedure

Status: `TODO`

### DEPLOY-004 — Production logging

Status: `TODO`

---

# Milestone 5 — Release

### RELEASE-001 — End-to-end acceptance suite

Status: `TODO`

### RELEASE-002 — Game Master documentation

Status: `TODO`

### RELEASE-003 — Player documentation

Status: `TODO`

### RELEASE-004 — Deployment documentation

Status: `TODO`

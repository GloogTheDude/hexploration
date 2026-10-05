# MVP Backlog

> Repository note: `BACKLOG.md` is not present. This file is the available MVP backlog and was used for task tracking without renaming it.

## P0 - Stabilisation

- [ ] TASK-001 Validate clean PostgreSQL installation
  - BLOCKED: Docker/PostgreSQL are healthy in the user's interactive shell, but the agent execution environment cannot access `/var/run/docker.sock` and cannot reach localhost:5435. Requires an agent environment with Docker/socket or database access.
- [ ] TASK-002 Validate Alembic migrations from empty database
  - BLOCKED: depends on the same unavailable PostgreSQL environment as TASK-001.
- [ ] TASK-003 Test campaign creation end-to-end
  - BLOCKED: end-to-end validation needs a PostgreSQL-backed application reachable from the agent environment.
- [ ] TASK-004 Test character creation end-to-end
  - BLOCKED: end-to-end validation needs a PostgreSQL-backed application reachable from the agent environment.
- [ ] TASK-005 Test world creation end-to-end
  - BLOCKED: end-to-end validation needs a PostgreSQL-backed application reachable from the agent environment.
- [ ] TASK-006 Test expedition creation end-to-end
  - BLOCKED: end-to-end validation needs a PostgreSQL-backed application reachable from the agent environment.
- [ ] TASK-007 Test expedition movement
  - BLOCKED: end-to-end validation needs a PostgreSQL-backed application reachable from the agent environment.
- [ ] TASK-008 Test player discovery / fog of war
  - BLOCKED: end-to-end validation needs a PostgreSQL-backed application reachable from the agent environment.

## P0 - Authentication

- [ ] TASK-020 Design authentication model
  - BLOCKED: choosing session versus token authentication is a product/security architecture decision; stop for user direction before implementing it.
- [x] TASK-021 Implement password hashing
  - Existing `pwdlib` hashing was verified and covered by `tests/test_user_service.py`.
- [ ] TASK-022 Implement login
  - BLOCKED: depends on the authentication model decision in TASK-020.
- [ ] TASK-023 Implement authenticated session/token
  - BLOCKED: depends on the authentication model decision in TASK-020.
- [ ] TASK-024 Remove explicit user_id trust
  - BLOCKED: depends on TASK-023.
- [ ] TASK-025 Protect DM endpoints
  - BLOCKED: depends on TASK-023 and TASK-024.
- [ ] TASK-026 Protect player resources
  - BLOCKED: depends on TASK-023 and TASK-024.
- [ ] TASK-027 Add authorization tests
  - BLOCKED: depends on the authentication model and protected endpoints.

## P1 - UX

- [x] TASK-040 Improve API error display
  - Primary frontend areas already extract FastAPI `detail` values and render actionable errors; coverage added in `tests/test_mvp_ux_assets.py`.
- [x] TASK-041 Add loading states
  - Existing campaign, dashboard, map and world-editor flows expose loading feedback; coverage added in `tests/test_mvp_ux_assets.py`.
- [x] TASK-042 Add save feedback
  - Existing terrain, world-editor, character-sheet and dashboard flows expose save/progress feedback; coverage added in `tests/test_mvp_ux_assets.py`.
- [x] TASK-043 Improve navigation
  - Existing primary pages expose cross-area navigation; coverage added in `tests/test_mvp_ux_assets.py`.

## P1 - Deployment

- [ ] TASK-060 Reproducible production setup
  - BLOCKED: production target and hosting/runtime requirements are not specified; choosing them would be a deployment architecture decision.
- [ ] TASK-061 Database backup
  - BLOCKED: backup destination, retention and secret-management policy require deployment input.
- [ ] TASK-062 Database restore procedure
  - BLOCKED: restore procedure depends on TASK-060/TASK-061 and would involve destructive database replacement.
- [ ] TASK-063 Production logging
  - BLOCKED: logging destination and retention requirements depend on the production target.

## P2 - Release

- [ ] TASK-080 End-to-end acceptance tests
  - BLOCKED: requires a PostgreSQL-backed application reachable from the agent environment.
- [ ] TASK-081 User documentation
  - BLOCKED: the final user workflow still depends on the unresolved authentication tasks.
- [ ] TASK-082 Deployment documentation
  - BLOCKED: depends on the unresolved production setup in TASK-060.

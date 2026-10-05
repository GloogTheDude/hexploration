# Hexploration — Agent Instructions

## 1. Project Goal

Hexploration is a web application for managing tabletop role-playing campaigns centered on exploration and hexcrawl gameplay.

The application is intended to let a Game Master:

- create and manage campaigns;
- build and maintain hex-based worlds;
- manage terrain, roads, rivers, areas, points of interest, and map versions;
- manage characters and expeditions;
- simulate travel and world time;
- manage discoveries and fog of war;
- schedule and resolve world events;
- expose appropriate campaign information to players.

The main product objective is to deliver a stable MVP by February 2027.

The core product concept is:

**persistent world map + expeditions + world time + fog of war + historical world events**

The current development phase is focused on completing and stabilizing the MVP, not expanding the product scope.

---

# 2. MVP Priorities

Work should be prioritized in this order:

1. Core campaign workflow
2. Data integrity
3. Authentication
4. Authorization
5. Expedition reliability
6. Map and fog-of-war reliability
7. Timeline and temporal-state reliability
8. Deployment
9. Backup and recovery
10. Documentation
11. UI/UX improvements

When choosing between technical elegance and completing the MVP safely, prefer the smallest maintainable solution that preserves the existing architecture.

---

# 3. Out of Scope

Do not implement new major product features unless explicitly requested.

The following are considered post-MVP features:

- combat system;
- realtime chat;
- advanced notifications;
- mobile application;
- custom rules engine;
- complex event automation;
- advanced realtime collaboration;
- Discord integration;
- marketplace;
- campaign sharing platform;
- unrelated visual redesigns;
- speculative infrastructure work.

Do not introduce one of these features simply because it appears useful.

Do not expand a task beyond its stated acceptance criteria.

---

# 4. Existing Architecture

The application uses:

## Backend

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## Frontend

- HTML
- CSS
- Vanilla JavaScript

Do not introduce a frontend framework unless explicitly requested.

## Main architectural layers

The intended backend flow is:

    routes
      ↓
    services
      ↓
    repositories
      ↓
    database

Responsibilities should remain separated.

### Routes

Routes are responsible for HTTP concerns:

- request parsing;
- validation;
- authentication/authorization entry points;
- HTTP status codes;
- response serialization.

Routes should remain thin.

Do not place substantial business logic in route handlers.

### Services

Services contain business logic.

Examples include:

- campaign rules;
- expedition behavior;
- world-time calculations;
- discoveries;
- fog-of-war rules;
- movement;
- temporal state resolution.

Prefer extending an existing service rather than creating parallel business logic elsewhere.

### Repositories

Repositories handle persistence and database queries.

Avoid embedding business rules in repositories.

### Models / DB

SQLAlchemy models represent persistent application state.

Database schema changes must be handled through Alembic migrations.

---

# 5. General Development Rules

Before modifying code:

1. Read the relevant implementation.
2. Read the relevant tests.
3. Identify the existing architectural pattern.
4. Search for similar functionality already implemented elsewhere.
5. Understand the expected behavior.
6. Determine the smallest safe change.

Prefer extending existing abstractions over introducing parallel systems.

Do not perform unrelated refactors.

Do not rename or reorganize unrelated files.

Do not rewrite working systems solely for stylistic reasons.

Avoid broad cleanup while implementing a focused task.

Preserve backward compatibility unless the task explicitly requires breaking behavior.

---

# 6. Autonomous Work Workflow

When instructed to work autonomously from the backlog:

1. Read this `AGENTS.md`.
2. Read `ROADMAP.md` if present.
3. Read `BACKLOG.md`.
4. Select the highest-priority incomplete task that is not blocked.
5. Inspect the relevant implementation and tests.
6. Establish the current test baseline when appropriate.
7. Implement the smallest complete solution.
8. Add or update tests.
9. Run focused tests for the changed functionality.
10. Run the complete fast test suite.
11. Fix regressions caused by the change.
12. Update the backlog with the result.
13. Continue with the next safe actionable task.

Do not wait for confirmation between ordinary implementation steps when the task is clear and within the established architecture.

Do not continue blindly when a stop condition defined below is reached.

---

# 7. Backlog Status

Use clear task states.

Recommended states:

    TODO
    IN_PROGRESS
    DONE
    BLOCKED
    NEEDS_POSTGRES_VALIDATION
    NEEDS_USER_DECISION

`DONE` means the implementation and all validation available in the current environment succeeded.

Do not mark a task `DONE` if required validation could not be performed.

Use `NEEDS_POSTGRES_VALIDATION` when implementation is complete and fast tests pass, but PostgreSQL-specific validation is still required outside the sandbox.

Use `NEEDS_USER_DECISION` when completing the task requires a product or architectural decision that cannot safely be inferred.

---

# 8. Testing

## Fast test suite

The standard validation command is:

    ./.venv/bin/pytest -q

Run relevant focused tests during development.

Before considering an ordinary task complete, run the complete fast test suite.

All previously passing tests must continue to pass.

New behavior should normally have automated test coverage.

Bug fixes should normally include a regression test demonstrating the corrected behavior.

Do not remove, weaken, skip, or rewrite a failing test merely to make the suite green unless the test is demonstrably obsolete because of an explicitly requested behavior change.

---

# 9. Important Test Database Limitation

The current pytest configuration uses an in-memory SQLite database.

The relevant configuration currently uses:

    sqlite+pysqlite:///:memory:

with:

    StaticPool

Therefore:

**A successful pytest run validates the application against the current SQLite test environment. It does not prove PostgreSQL compatibility.**

Never report SQLite test success as PostgreSQL validation.

---

# 10. PostgreSQL Sandbox Limitation

The agent execution environment cannot currently run PostgreSQL.

Previous environment investigation established that the sandbox prevents PostgreSQL from creating:

- TCP sockets;
- Unix-domain sockets.

Docker CLI may be installed, but the agent does not have usable access to the Docker daemon.

Do not repeatedly attempt to:

- start PostgreSQL in the sandbox;
- create temporary PostgreSQL clusters;
- bypass socket restrictions;
- access the host Docker socket;
- expose or discover the developer's local PostgreSQL instance.

These failures are environmental and should not trigger repeated workarounds.

Use SQLite tests for normal fast validation.

---

# 11. PostgreSQL-Specific Validation

PostgreSQL validation is required for changes involving, among other things:

- Alembic migrations;
- schema changes;
- PostgreSQL-specific SQL;
- PostgreSQL-specific column types;
- indexes;
- unique constraints;
- foreign-key behavior;
- cascading behavior;
- database-level defaults;
- transaction behavior;
- locking;
- isolation;
- database-generated values;
- PostgreSQL-specific functions;
- raw SQL;
- data migrations.

When PostgreSQL validation is required but unavailable:

1. complete all safe implementation work;
2. run all relevant SQLite tests;
3. run the complete SQLite test suite;
4. inspect the migration or SQL statically;
5. document what PostgreSQL validation remains;
6. provide the exact local validation commands when possible;
7. mark the task `NEEDS_POSTGRES_VALIDATION`;
8. continue with another independent task if safe.

Do not block the entire backlog because one task requires PostgreSQL validation.

---

# 12. Database Safety

Never connect to, modify, reset, migrate, truncate, or delete data from an unknown or developer-owned database unless explicitly authorized.

Never assume the database configured in `.env` is disposable.

Never run destructive commands against the configured development database merely for testing.

Examples of potentially destructive operations include:

    alembic downgrade base
    dropdb
    DROP DATABASE
    DROP TABLE
    TRUNCATE
    DELETE without an appropriate filter

Treat persistent developer data as non-disposable.

Test databases must be explicitly identified as test databases.

---

# 13. Alembic Rules

Every persistent schema change requires an Alembic migration.

Do not rely only on:

    Base.metadata.create_all()

for production schema evolution.

Before creating a migration:

1. inspect existing migrations;
2. inspect the current SQLAlchemy models;
3. inspect the current Alembic head;
4. understand the existing migration chain.

Do not modify an existing migration that may already have been applied unless explicitly instructed to repair migration history.

Prefer adding a new migration.

Migration upgrades should preserve existing data whenever reasonably possible.

Potentially destructive migrations require explicit attention and should not be silently introduced.

Because PostgreSQL cannot run inside the sandbox, migration work generally requires `NEEDS_POSTGRES_VALIDATION` before final acceptance.

---

# 14. Authentication and Authorization

Authentication and authorization are MVP-critical functionality.

When working on security:

- never trust a user ID supplied by the client merely because it exists;
- derive identity from the authenticated session/token once authentication exists;
- verify ownership and campaign membership;
- distinguish Game Master permissions from player permissions;
- prevent cross-user and cross-campaign data access;
- prefer deny-by-default behavior for protected resources.

Security checks belong on the server.

Do not rely on the frontend to enforce authorization.

Add negative authorization tests, not only successful-access tests.

---

# 15. Secrets

Never:

- commit `.env`;
- commit passwords;
- commit API keys;
- print secrets unnecessarily;
- copy credentials into documentation;
- expose complete `DATABASE_URL` values in logs or reports.

When reporting database URLs, redact credentials.

For example:

    postgresql+psycopg://***:***@host/database

Do not replace existing secrets unless explicitly requested.

---

# 16. Core Campaign Workflow

The critical MVP user flow is:

    user
      ↓
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
    discovery
      ↓
    persisted campaign state

Changes affecting this flow should receive higher scrutiny.

When practical, preserve or add tests covering complete workflow transitions rather than testing only isolated implementation details.

---

# 17. Temporal Model

World time is a core domain concept.

Do not casually replace historical or temporal state with mutable "current state" fields if the existing architecture resolves state according to campaign time.

Changes involving:

- WorldEvent;
- expedition clocks;
- map state over time;
- weather;
- roads;
- bridges;
- POIs;
- discoveries;
- temporal versions;

must preserve historical consistency.

Two expeditions existing at different campaign times may legitimately observe different states of the same world object.

Treat this as intentional domain behavior.

---

# 18. Fog of War and Player Knowledge

Player knowledge must remain separate from Game Master knowledge.

Do not expose complete world state to player-facing endpoints merely because the frontend currently hides it.

Visibility restrictions must be enforced server-side where appropriate.

Be careful when modifying:

- discovered hexes;
- visible hexes;
- visited locations;
- POI knowledge;
- player map payloads;
- expedition visibility.

Avoid information leaks through API responses.

---

# 19. Error Handling

Prefer explicit failures over silent corruption.

API errors should:

- use appropriate HTTP status codes;
- provide useful but non-sensitive messages;
- avoid leaking internal implementation details;
- remain consistent with existing project conventions.

Do not catch broad exceptions merely to suppress failures.

Unexpected failures should remain observable through logs or tests.

---

# 20. Refactoring Policy

Refactoring is allowed when necessary to safely complete the current task.

Large independent refactors are not part of ordinary backlog work.

A refactor should normally satisfy at least one of these conditions:

- necessary to implement the requested behavior safely;
- removes duplication directly blocking the task;
- fixes an architectural problem demonstrated by tests;
- substantially reduces risk in the code being modified.

Do not perform speculative refactoring.

If a larger architectural refactor appears valuable, document it as a separate proposed task rather than silently including it.

---

# 21. Dependencies

Do not add a new dependency when the standard library or an existing project dependency reasonably solves the problem.

Before adding a dependency:

1. confirm the project does not already contain an equivalent solution;
2. explain why it is necessary;
3. prefer maintained and focused packages;
4. update dependency metadata consistently.

Do not introduce major infrastructure dependencies for convenience.

---

# 22. Frontend Changes

The current frontend uses HTML, CSS, and vanilla JavaScript.

Preserve this architecture unless explicitly instructed otherwise.

Frontend changes should:

- preserve existing navigation;
- display backend errors appropriately;
- provide loading feedback for meaningful asynchronous actions;
- provide clear save/success states where needed;
- avoid exposing privileged information;
- remain usable on typical laptop displays.

Do not perform a complete visual redesign while fixing functional issues.

---

# 23. Documentation

Update documentation when behavior, installation, configuration, or user workflows materially change.

Documentation should distinguish between:

- developer setup;
- deployment;
- Game Master usage;
- player usage.

Avoid turning the main README into an unstructured development diary.

Prefer concise documentation describing the current system.

---

# 24. Git Discipline

Keep changes focused.

Before considering a task complete:

- inspect the diff;
- ensure unrelated files were not modified;
- ensure temporary files are not included;
- ensure secrets are not included;
- ensure generated artifacts are intentional.

Do not rewrite unrelated history.

Do not force-push.

Do not create commits unless the current workflow explicitly authorizes autonomous commits.

When commits are authorized, prefer one coherent commit per completed backlog task or tightly related group of changes.

Use descriptive commit messages.

---

# 25. Stop Conditions

Stop autonomous implementation for the current task and request guidance when:

- requirements are materially ambiguous;
- two plausible interpretations would produce significantly different behavior;
- a major architectural decision is required;
- existing user data could be destroyed;
- migration safety cannot reasonably be determined;
- a security decision requires product input;
- completing the task requires expanding MVP scope;
- existing behavior appears intentionally different from the backlog requirement;
- credentials or external infrastructure are required and unavailable;
- a required destructive operation has not been explicitly authorized.

When stopping:

1. explain the blocker;
2. identify the relevant files/code;
3. describe the available options;
4. recommend an option when possible;
5. mark the task appropriately.

Do not invent requirements merely to continue the loop.

---

# 26. Conditions That Do NOT Require Stopping

Do not stop merely because:

- a normal implementation detail needs to be chosen;
- a small internal refactor is required;
- tests initially fail because of the new implementation;
- formatting/lint issues occur;
- a clearly related bug is discovered and can safely be fixed;
- PostgreSQL validation is unavailable but the task can otherwise be completed safely.

Use engineering judgment for ordinary implementation decisions.

---

# 27. Handling Existing Failures

Before beginning substantial autonomous work, establish the relevant baseline when practical.

If a test was already failing before the current task:

- do not automatically attribute
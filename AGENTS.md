# AGENTS.md

## 1. Purpose

This repository is developed with autonomous coding agents.

Agents are expected to:

- inspect the existing architecture before modifying it;
- preserve established project conventions;
- work through backlog items autonomously when requirements are clear;
- implement the smallest coherent change;
- add or update tests;
- run validation;
- update BACKLOG.md;
- create focused Git commits when work is validated;
- stop only when a real product, architecture, safety, or data decision
  requires user input.

Do not ask for confirmation for ordinary implementation choices.

Do not make speculative product decisions when requirements are genuinely
ambiguous.

---

# 2. Project

Project:

    Hexploration

Repository:

    hexploration_v1

Primary stack:

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- SQLite for fast/default automated tests
- HTML
- CSS
- vanilla JavaScript

The production/development persistence target is PostgreSQL.

SQLite exists primarily as a fast automated test backend.

Behavior that passes SQLite but has not been validated on PostgreSQL must
not automatically be assumed PostgreSQL-compatible when the change is
database-sensitive.

---

# 3. Sources of truth

Before beginning substantial work, read:

    AGENTS.md
    BACKLOG.md

Also read:

    ROADMAP.md

when it exists and is relevant to the requested work.

The current codebase is the source of truth for implementation details.

BACKLOG.md is the source of truth for tracked work and task status.

Do not assume that an old task description perfectly reflects the current
implementation.

Inspect the code first.

---

# 4. General workflow

For each task or coherent subtask:

1. read the relevant backlog entry;
2. inspect the affected implementation;
3. inspect related tests;
4. establish current behavior;
5. identify the smallest safe change;
6. implement it;
7. add or update focused tests;
8. run focused tests;
9. run the complete default test suite;
10. update BACKLOG.md;
11. determine whether PostgreSQL validation is required;
12. create a focused Git commit when allowed by the rules below;
13. continue to the next safely actionable task.

Do not stop merely because one implementation detail was not explicitly
specified if the correct choice can be inferred safely from the existing
architecture and project conventions.

---

# 5. Backlog states

Use the following states consistently.

## TODO

Work has not started.

## IN_PROGRESS

Implementation is actively underway.

## BLOCKED

The task cannot proceed because of an external or technical dependency.

Document the blocker.

## NEEDS_USER_DECISION

Implementation requires a genuine product or architecture decision that
cannot safely be inferred.

Document:

- the decision required;
- available options;
- consequences;
- recommended option when appropriate.

Continue independent tasks when possible.

## NEEDS_POSTGRES_VALIDATION

Implementation is complete and local/default tests pass, but the task
contains database-sensitive behavior that requires validation against
real PostgreSQL outside the agent sandbox.

Document the exact validation command.

## DONE

Implementation is complete and all validation required for that task has
passed.

Do not mark a PostgreSQL-sensitive task DONE until PostgreSQL validation
has actually been reported successful.

---

# 6. Testing

## Default suite

The default test command is:

    ./.venv/bin/pytest -q

Run focused tests first when practical.

Then run the complete suite before considering a coherent task complete.

Do not weaken, delete, skip, or rewrite a useful test merely to make a
new implementation pass.

When behavior intentionally changes, update the test to express the new
intended behavior.

Preserve lower-level unit/service tests when HTTP authentication is not
relevant to what they test.

---

# 7. PostgreSQL testing

Tests use SQLite by default unless TEST_DATABASE_URL is provided.

PostgreSQL tests use:

    TEST_DATABASE_URL

Example:

    TEST_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST:PORT/hexploration_test' \
    ./.venv/bin/pytest -q

TEST_DATABASE_URL must point to a dedicated disposable test database.

The configured database name must clearly indicate that it is a test
database.

Never silently fall back from a requested PostgreSQL validation to
SQLite.

Never claim PostgreSQL validation based only on SQLite results.

---

# 8. Database safety

The developer database is valuable persistent state.

Never:

- drop it;
- recreate it;
- truncate it;
- downgrade it;
- stamp it;
- reset it;
- clear application data;
- run destructive experiments against it.

The known development database is:

    hexploration

Treat it as protected.

Database experiments and migration validation must use a dedicated
database such as:

    hexploration_test

When database identity is uncertain, do not perform destructive
operations.

---

# 9. Alembic

All persistent schema changes require Alembic migrations.

Do not use SQLAlchemy metadata creation as a replacement for migrations
in application environments.

Historical migrations must be deterministic.

Never make a historical migration depend dynamically on the current
SQLAlchemy metadata.

A migration should represent the schema transition belonging to that
revision.

Before creating a migration:

1. inspect the current Alembic head;
2. inspect nearby migrations;
3. inspect the SQLAlchemy model;
4. preserve naming and constraint conventions.

After creating a migration:

    ./.venv/bin/alembic heads

must show the expected graph.

When PostgreSQL runtime validation cannot be performed by the agent,
mark the relevant work:

    NEEDS_POSTGRES_VALIDATION

and provide exact commands for validation.

Do not claim a migration works on PostgreSQL until it has actually been
tested there.

---

# 10. Existing migration history

The historical baseline migration has been repaired so that the migration
chain can reproduce the schema from a fresh PostgreSQL database.

Do not reintroduce dynamic:

    Base.metadata.create_all()

or:

    Base.metadata.drop_all()

into historical Alembic migrations.

The migration chain must remain reproducible from base to head.

When modifying database behavior, preserve that property.

---

# 11. SQLAlchemy compatibility

The application targets PostgreSQL.

SQLite compatibility is useful for fast tests but must not force
production behavior into SQLite-specific patterns.

Pay particular attention to backend differences involving:

- timezone-aware DateTime;
- enums;
- JSON;
- foreign keys;
- unique constraints;
- CHECK constraints;
- transaction behavior;
- sequences and generated primary keys;
- cascading behavior.

When behavior differs, prefer explicit portable application logic or
PostgreSQL-correct behavior.

---

# 12. Authentication architecture

Authentication uses server-side opaque sessions.

The architecture is:

    credentials
        ↓
    password verification
        ↓
    opaque session token
        ↓
    SHA-256 token hash persisted server-side
        ↓
    HttpOnly session cookie
        ↓
    get_current_user()

Do not replace this architecture with JWT without an explicit
architecture decision.

Do not introduce:

- OAuth;
- MFA;
- Redis sessions;
- external identity providers;
- generic authentication frameworks;

unless explicitly required by a backlog item or user decision.

Passwords must never be stored in plaintext.

Use the existing pwdlib/Argon2 password infrastructure.

Unknown or malformed password hashes must fail safely.

Never interpret an unknown hash as plaintext.

---

# 13. Session security

Raw session tokens must not be persisted in the database.

Raw session tokens must not be logged.

The browser session cookie is HttpOnly.

The frontend must not:

- read the session token;
- copy it to localStorage;
- copy it to sessionStorage;
- create a parallel authentication mechanism.

Authenticated frontend identity comes from:

    GET /auth/me

The backend remains the source of truth.

---

# 14. Authorization

Never trust a client-supplied user identifier as proof of caller identity.

Caller identity must come from:

    get_current_user()

However, not every user_id is impersonation.

For every identity parameter distinguish between:

A. authenticated caller identity;
B. legitimate target/domain identity.

Replace A with authenticated identity.

Retain B when it is legitimate, but authorize whether the caller may act
on that target.

---

# 15. Campaign authorization

Campaign roles are contextual.

Use:

    CampaignMembership

as the source of role information.

A user may be:

    DM in campaign A
    PLAYER in campaign B
    not a member of campaign C

Do not introduce a global is_dm flag.

Expected semantics:

Unauthenticated:

    401 Unauthorized

Authenticated but outside the relevant campaign:

    prefer 404 Not Found

when hiding resource existence is useful.

Authenticated campaign member without sufficient permission:

    403 Forbidden

Campaign DM checks must derive from CampaignMembership.

---

# 16. Expedition authorization

Campaign membership alone does not imply player access to an expedition.

A PLAYER must actually participate in the expedition where participation
is required.

A campaign DM may access the expedition according to existing DM
authorization rules.

For player-facing expedition resources:

- unauthenticated -> 401;
- outside campaign -> normally 404;
- campaign PLAYER but non-participant -> 403;
- participating PLAYER -> allowed;
- campaign DM -> allowed where specified.

Do not weaken these rules merely to simplify frontend behavior.

---

# 17. Fog of war

Player-facing endpoints must not expose DM-only or undiscovered
information.

Authorization and information filtering are separate requirements.

A correctly authorized player may still receive too much information if
the payload is not filtered.

When modifying player-facing data, inspect for leakage involving:

- undiscovered hexes;
- terrain;
- POIs;
- DM descriptions;
- DM pings;
- semantic features;
- historical observations;
- hidden metadata;
- character-specific knowledge.

The player-map endpoint is specifically intended to represent the
filtered player view.

When a DM requests player-map, it should still return the player-view
representation rather than unrestricted DM knowledge.

---

# 18. CSRF

Authentication uses cookies.

HttpOnly protects token confidentiality from JavaScript but does not
protect against CSRF.

Preserve the existing Origin/Referer protection for authenticated unsafe
requests.

Unsafe methods include:

    POST
    PUT
    PATCH
    DELETE

Do not introduce a second CSRF system without a demonstrated need.

Do not weaken CSRF protection to fix frontend request failures.

---

# 19. Frontend authentication

Frontend startup must establish authentication before initializing
protected workflows.

Preferred flow:

    page load
        ↓
    GET /auth/me
        ↓
    authenticated?
       /      \
      no      yes
      |        |
    auth UI   initialize application

Do not fire protected application requests first and discover
authentication failure afterward.

A 401 from a protected request invalidates frontend authenticated state.

A 403 or 404 must not automatically log the user out.

---

# 20. Registration

Public self-registration exists for the MVP.

Registration must not allow users to assign themselves:

- campaign roles;
- DM privileges;
- campaign memberships;
- arbitrary permissions.

Registration and authentication remain separate operations.

Preferred successful flow:

    create account
        ↓
    normal login
        ↓
    /auth/me
        ↓
    authenticated application

Do not fabricate authenticated frontend state from a registration
response.

---

# 21. Legacy/global map routes

Some map editor routes historically operate without campaign context,
including routes under patterns such as:

    /api/map
    /api/hex/*
    /api/newmap/*

Do not invent campaign authorization for a route that lacks sufficient
campaign context.

Audit usage before modifying or removing legacy routes.

If architecture changes are required, record them as explicit backlog
work rather than hiding them inside unrelated tasks.

---

# 22. Scope discipline

Avoid unrelated refactors.

Do not opportunistically rewrite modules merely because they could be
cleaner.

A task should modify only what is required for:

- the requested behavior;
- correctness;
- security;
- required tests;
- necessary supporting architecture.

When a larger refactor would be useful but is not required, add or
propose a backlog item instead.

---

# 23. Secrets

Never commit:

    .env

or files containing credentials, API keys, session tokens, passwords or
other secrets.

Do not print secrets unnecessarily.

Do not place real credentials in:

- source files;
- tests;
- documentation;
- commit messages.

Use placeholders in documentation.

Local development credentials supplied by the user may be used for
explicit local commands but must not be persisted into tracked files.

---

# 24. Local artifacts

Do not commit local operational artifacts unless explicitly requested.

Examples include:

- database dumps;
- backups;
- generated schema dumps;
- temporary files;
- logs;
- coverage output;
- caches;
- local environment files.

Examples that should normally remain untracked/ignored:

    backups/
    *.dump
    development-schema.sql
    test-schema.sql
    .env
    __pycache__/
    .pytest_cache/

Do not delete a user's backup merely because it should not be committed.

---

# 25. Existing working-tree changes

The working tree may contain changes from:

- the current task;
- previous completed tasks;
- user edits;
- other agents.

Never assume every modified or untracked file belongs to the current
task.

Before staging:

    git status --short
    git diff -- <candidate files>

Inspect untracked files before staging them.

Preserve unrelated changes.

Do not revert, overwrite, clean or discard user work merely to obtain a
clean working tree.

---

# 26. Autonomous Git commits

Agents ARE AUTHORIZED to create local Git commits autonomously.

A commit may be created when:

- the work forms a coherent completed unit;
- focused tests pass;
- the complete required local/default test suite passes;
- there is no known regression in the committed scope;
- BACKLOG.md accurately reflects the state of the work;
- staged files have been inspected;
- unrelated working-tree changes are excluded;
- secrets and local artifacts are excluded.

Prefer one focused commit per completed backlog task or coherent
implementation unit.

Good examples:

    add server-side authentication sessions
    enforce campaign and expedition authorization
    integrate frontend authentication flow
    add public registration flow

Avoid vague messages such as:

    changes
    fixes
    update stuff
    work

---

# 27. Staging rules

Never use:

    git add .
    git add -A

Stage files explicitly.

Examples:

    git add services/auth_service.py
    git add routes/auth_routes.py
    git add tests/test_authentication_foundation.py

or another explicit file list.

Before committing, always inspect:

    git status --short
    git diff --cached --stat
    git diff --cached

Verify that the staged diff contains only the intended coherent change.

If a file contains unrelated modifications mixed with task changes, do
not blindly stage the entire file.

Separate the changes safely when practical.

If they cannot safely be separated, leave the file uncommitted and
report it.

---

# 28. Commit validation

Before each commit, run the validation appropriate to that coherent
change.

At minimum:

1. focused tests;
2. complete default suite:

       ./.venv/bin/pytest -q

For documentation-only changes, use judgment.

Do not rerun expensive unrelated validation unnecessarily when the code
has not changed since a successful full validation.

If multiple already-completed coherent tasks are being committed
retroactively and the current full suite validates their combined final
state, the agent may use that successful validation while carefully
partitioning commits by diff/history.

Do not manufacture or claim historical test results that were not
actually observed.

---

# 29. PostgreSQL-sensitive commits

A task requiring PostgreSQL validation may be committed before that
external validation only when:

- all sandbox/default validation passes;
- the implementation is otherwise complete;
- BACKLOG.md remains marked NEEDS_POSTGRES_VALIDATION;
- the commit does not claim PostgreSQL validation.

Once the user reports successful PostgreSQL validation:

1. update BACKLOG.md to record it;
2. run relevant local/default checks if code changed;
3. commit the validation/status update when appropriate.

If PostgreSQL validation fails, do not mark the task DONE.

Fix the issue and repeat validation.

---

# 30. Prohibited Git operations

Unless the user explicitly authorizes them, do not:

- push;
- force-push;
- rebase;
- amend existing commits;
- reset --hard;
- reset user work;
- clean the working tree;
- delete branches;
- rewrite published history;
- squash existing history.

Do not use destructive Git commands to make the repository appear clean.

Local commits are authorized.

Remote publication is not.

---

# 31. Retroactive commits

When validated work already exists in the working tree from previous
agent tasks, the agent may organize it into retroactive local commits.

Before doing so:

1. inspect git status;
2. inspect git log;
3. inspect every modified/untracked candidate file;
4. identify which completed backlog task introduced each change;
5. exclude unrelated/user/local-artifact changes;
6. partition the work into coherent commits;
7. verify each staged diff;
8. commit in logical dependency order.

Do not arbitrarily split files if doing so would create invalid
intermediate states.

When clean separation is impossible, prefer a larger coherent commit over
unsafe patch manipulation.

The final repository state must preserve all validated behavior.

---

# 32. Commit dependency order

When committing multiple completed tasks retroactively, use logical
dependency order.

For example:

    database/migration foundation
        ↓
    authentication foundation
        ↓
    authorization
        ↓
    frontend authentication
        ↓
    frontend registration

Do not create commits whose content depends on code introduced only by a
later commit.

Each commit should represent a comprehensible repository state whenever
practical.

---

# 33. BACKLOG.md and commits

BACKLOG.md may span multiple tasks.

When partitioning retroactive commits, stage the appropriate backlog
changes with the corresponding implementation when they can be separated
safely.

If BACKLOG.md changes are too interdependent to partition without
rewriting history inaccurately, include the final backlog state in the
last relevant commit.

Do not falsify task chronology merely to make commit boundaries prettier.

---

# 34. Commit messages

Use concise imperative commit subjects.

Preferred style:

    add opaque authentication sessions
    enforce campaign authorization
    secure expedition player map access
    integrate frontend login and logout
    add frontend account registration

Optionally include a commit body when important context is not obvious.

A useful body may mention:

- security behavior;
- migration revision;
- important compatibility considerations;
- test result.

Do not include secrets or local credentials.

Do not claim PostgreSQL validation unless it actually occurred.

---

# 35. No automatic push

Creating local commits does NOT authorize pushing them.

After committing, report:

- commit hash;
- commit subject;
- files/scope;
- validation performed;
- remaining uncommitted changes.

Do not run:

    git push

unless explicitly requested by the user.

---

# 36. Error handling

Do not hide exceptions merely to make tests pass.

Translate expected domain/application failures into appropriate API
responses.

Unexpected failures should remain observable through normal application
error handling/logging.

Security-sensitive failures should not expose internal details to the
client.

---

# 37. HTTP semantics

Use HTTP status codes consistently.

Typical expectations:

    400  malformed domain request
    401  authentication required/invalid
    403  authenticated but forbidden
    404  missing resource or intentionally hidden cross-scope resource
    409  state/uniqueness conflict
    422  request validation failure

Preserve established project behavior when more specific semantics
already exist.

---

# 38. Security regressions

When modifying authentication, authorization, invitations, campaigns,
characters, expeditions or fog-of-war behavior, consider tests for:

- caller impersonation;
- cross-user access;
- cross-campaign access;
- PLAYER vs DM privilege;
- expedition participation;
- hidden-resource enumeration;
- hidden map information;
- plaintext password persistence;
- raw session token persistence;
- CSRF behavior.

Security fixes should include regression tests whenever practical.

---

# 39. Dependency changes

Do not add a dependency when the standard library or an existing project
dependency adequately solves the problem.

Before adding a dependency:

1. inspect existing requirements/project configuration;
2. justify why it is needed;
3. keep scope minimal.

Do not introduce large frameworks for small problems.

---

# 40. Frontend conventions

The current frontend uses HTML, CSS and vanilla JavaScript.

Do not introduce React, Vue, Svelte or another frontend framework as part
of an unrelated task.

Reuse existing frontend helpers and state patterns where practical.

Avoid duplicating API/authentication handling across pages.

---

# 41. Formatting and code quality

Follow existing project style.

Prefer:

- clear names;
- explicit control flow;
- small helpers;
- typed Python where consistent with surrounding code;
- minimal comments explaining non-obvious intent.

Avoid:

- speculative abstractions;
- premature generic frameworks;
- dead code;
- commented-out implementations;
- unrelated formatting churn.

Run:

    git diff --check

before committing.

Fix whitespace errors introduced by the current task.

Do not modify unrelated files solely to remove pre-existing whitespace
warnings.

---

# 42. Stop conditions

Use NEEDS_USER_DECISION only for genuine decisions.

Examples:

- unclear ownership semantics;
- incompatible product requirements;
- a required schema change whose design is not established;
- destructive data migration;
- security behavior with multiple materially different valid policies.

Do not stop for:

- naming a private helper;
- choosing ordinary implementation structure;
- adding obvious tests;
- fixing a directly caused regression;
- straightforward use of existing project patterns.

A blocked task should not prevent progress on independent tasks.

---

# 43. Definition of done

A task is DONE when all applicable conditions are satisfied:

- requested behavior is implemented;
- architecture remains coherent;
- security requirements are preserved;
- focused tests pass;
- complete default tests pass;
- PostgreSQL validation passes when required;
- Alembic migration is validated when required;
- BACKLOG.md is accurate;
- no known regression remains;
- relevant work is committed according to this policy.

If external PostgreSQL validation remains:

    NEEDS_POSTGRES_VALIDATION

is the correct state, not DONE.

---

# 44. Final task report

After autonomous work, report concisely:

1. what was implemented;
2. important architecture/security decisions;
3. tests executed and results;
4. PostgreSQL validation status;
5. migrations created or changed;
6. backlog statuses;
7. commits created;
8. remaining uncommitted files;
9. NEEDS_USER_DECISION / BLOCKED items;
10. recommended next backlog task.

Do not claim validation that was not actually performed.
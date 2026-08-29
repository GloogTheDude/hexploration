# Hexploration — recovered project v2

This is the corrected complete recovery archive.

Corrections included in v2:

- `db/__init__.py` exports `Base`, so Alembic's `from db import Base` works.
- `.env.example` is included explicitly.
- `recover.sh` reuses an existing `hexploration_postgres` container instead of trying to create a conflicting duplicate.
- Alembic migration head remains the corrected `0002_exp_weather_transport`.
- Persistent expedition weather/transport is already integrated into the SQLAlchemy model and movement service.

## Recommended recovery

Keep the broken project as a backup and unpack this archive beside it.

Then, from the recovered project directory:

```bash
bash recover.sh
```

The script:

1. creates `.env` only if missing;
2. creates/uses `.venv`;
3. installs requirements;
4. reuses the existing `hexploration_postgres` container when present;
5. starts it if necessary;
6. runs Alembic through the current head;
7. verifies SQLAlchemy metadata loads.

After success:

```bash
source .venv/bin/activate
uvicorn main:app --reload
```

Useful checks:

```bash
pytest
python tests/manual_test_movement.py
python tests/manual_test_terrain_costs.py
python tests/manual_test_weather_transport.py
```

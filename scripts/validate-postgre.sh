docker exec hexploration_postgres pg_isready \
    -U hexploration \
    -d hexploration

./.venv/bin/alembic current
./.venv/bin/alembic upgrade head
./.venv/bin/pytest -q
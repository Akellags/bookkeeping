Absolutely — below is a **segregated document-style version** you can paste into your internal docs.

---

# 1. SQLite → PostgreSQL Migration Guide

## Objective

Migrate the current development database from **SQLite** to **PostgreSQL on Cloud SQL**, while keeping the FastAPI application ready for Cloud Run deployment.

SQLite is fine for local development, but PostgreSQL is the better production target here. Alembic is the standard migration tool used with SQLAlchemy, and SQLAlchemy supports both SQLite and PostgreSQL through dialects/drivers. ([Alembic][1])

## Recommended migration approach

Use this sequence:

1. make the SQLAlchemy models PostgreSQL-safe
2. introduce Alembic if not already present
3. create a fresh PostgreSQL schema from migrations
4. export data from SQLite
5. transform and load the data into PostgreSQL
6. point the application to PostgreSQL
7. validate the application end to end

Alembic supports schema versioning and autogeneration against SQLAlchemy metadata, which makes it the right tool for moving from a local SQLite setup to a managed PostgreSQL target. ([Alembic][2])

## Phase A — Prepare the application

### A1. Add PostgreSQL driver

For a current SQLAlchemy setup, `psycopg` (Psycopg 3) is the modern default PostgreSQL driver. SQLAlchemy’s current docs note that the default PostgreSQL DBAPI driver changed to `psycopg`. ([SQLAlchemy][3])

Example dependency set:

```txt
sqlalchemy
alembic
psycopg[binary]
```

### A2. Split database URLs by environment

Keep separate URLs:

```env
# local dev
DATABASE_URL=sqlite:///./app.db

# postgres / cloud sql target
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
```

SQLAlchemy engines are configured from database URLs, and the PostgreSQL dialect uses an installed DBAPI driver. ([SQLAlchemy][4])

### A3. Review SQLite-specific model assumptions

Before migrating, check for things that behave differently between SQLite and PostgreSQL:

* implicit autoincrement assumptions
* weak SQLite typing
* boolean handling
* datetime defaults
* JSON/text fields
* raw SQL written in SQLite syntax

Also note that Alembic has special “batch” migration support specifically because SQLite has DDL limitations compared with other databases. ([Alembic][5])

## Phase B — Introduce Alembic

### B1. Initialize Alembic

Run:

```bash
alembic init alembic
```

Alembic’s tutorial and docs describe this as the standard starting point for migration management. ([Alembic][2])

### B2. Point Alembic to your SQLAlchemy metadata

In `alembic/env.py`, wire in your app’s metadata:

```python
from app.db.base import Base
target_metadata = Base.metadata
```

### B3. Configure DB URL

Either set `sqlalchemy.url` in `alembic.ini` or load it from environment variables in `env.py`. Alembic compares the target database schema to SQLAlchemy metadata using the configured database URL. ([Alembic][6])

## Phase C — Create the PostgreSQL schema

### C1. Generate initial migration

If migrations do not already exist:

```bash
alembic revision --autogenerate -m "initial schema"
```

Alembic’s `--autogenerate` creates candidate migrations by comparing the current database schema with SQLAlchemy metadata. ([Alembic][6])

### C2. Review the migration manually

Do not blindly trust autogeneration. Check:

* primary keys
* indexes
* unique constraints
* foreign keys
* default values
* column types

Alembic autogeneration is intended to create candidate migrations, which should still be reviewed before use. ([Alembic][6])

### C3. Apply migration to PostgreSQL

Point Alembic to the PostgreSQL database and run:

```bash
alembic upgrade head
```

This creates the schema in PostgreSQL using your migration history. Alembic migration directives are applied through the migration runtime and operation system. ([Alembic][7])

## Phase D — Migrate the data

There are two reasonable paths.

### Option 1 — Small startup-friendly path

For a small dataset, write a one-time Python migration script:

1. connect to SQLite
2. read rows table by table
3. transform data where needed
4. insert into PostgreSQL in dependency order

This is usually the cleanest option for startup systems because it lets you explicitly fix type mismatches and bad legacy data during the move.

### Option 2 — Dump and import

Possible for simple databases, but usually less controlled than a scripted move when moving from SQLite to PostgreSQL.

For your case, I recommend **Option 1**.

## Sample one-time migration script

This is a simple pattern using SQLAlchemy ORM/core. Adjust table imports to your app.

```python
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.order import Order

sqlite_engine = create_engine("sqlite:///./app.db")
pg_engine = create_engine("postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME")

TABLES_IN_ORDER = [
    User,
    Order,
]

def copy_table(model, source_session: Session, target_session: Session):
    rows = source_session.execute(select(model)).scalars().all()
    for row in rows:
        data = {
            c.name: getattr(row, c.name)
            for c in model.__table__.columns
        }
        target_session.add(model(**data))
    target_session.commit()

def main():
    with Session(sqlite_engine) as source_session, Session(pg_engine) as target_session:
        for model in TABLES_IN_ORDER:
            copy_table(model, source_session, target_session)

if __name__ == "__main__":
    main()
```

## Data migration rules

During the move, verify these specifically:

### IDs and sequences

If IDs are copied explicitly, PostgreSQL sequences may need to be reset afterward so future inserts do not collide.

### Booleans

SQLite is permissive; PostgreSQL is stricter. Clean up inconsistent boolean values before insert.

### Datetimes

Make sure formats are normalized. Prefer timezone-aware timestamps in production if your app supports them.

### JSON fields

If you previously stored JSON-like text in SQLite, decide whether the PostgreSQL target column should remain text or become JSON/JSONB. PostgreSQL has strong native support for JSON types in SQLAlchemy. ([SQLAlchemy][8])

## Phase E — Cut over the application

### E1. Update the app connection string

Switch the app from:

```env
DATABASE_URL=sqlite:///./app.db
```

to:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DB_NAME
```

### E2. Run migrations against PostgreSQL

Before starting the app in the new environment:

```bash
alembic upgrade head
```

### E3. Smoke test the app

Test:

* login/auth flows
* create/read/update/delete endpoints
* pagination/filtering
* unique constraints
* background tasks that write to DB
* report/export screens

## Recommended final structure

Keep the following separation:

* **SQLAlchemy models** = source of schema truth
* **Alembic** = schema evolution tool
* **one-time migration script** = data copy from SQLite to PostgreSQL
* **Cloud SQL PostgreSQL** = production database

## Migration checklist

Use this mini-checklist while executing:

* all models reviewed for SQLite-specific assumptions
* PostgreSQL driver installed
* Alembic initialized
* initial migration generated and reviewed
* PostgreSQL schema created with `alembic upgrade head`
* one-time data migration script tested locally
* row counts matched between SQLite and PostgreSQL
* primary keys and sequences validated
* app switched to PostgreSQL URL
* smoke tests passed

---


If you want, next I can format this into a **clean handoff document** with headings like **Purpose / Scope / Steps / Risks / Rollback** so it reads like formal project documentation.

[1]: https://alembic.sqlalchemy.org/?utm_source=chatgpt.com "Alembic's documentation! - SQLAlchemy"
[2]: https://alembic.sqlalchemy.org/en/latest/tutorial.html?utm_source=chatgpt.com "Tutorial — Alembic 1.18.4 documentation"
[3]: https://docs.sqlalchemy.org/en/latest/changelog/migration_21.html?utm_source=chatgpt.com "What's New in SQLAlchemy 2.1?"
[4]: https://docs.sqlalchemy.org/en/latest/core/engines.html?utm_source=chatgpt.com "Engine Configuration — SQLAlchemy 2.1 Documentation"
[5]: https://alembic.sqlalchemy.org/en/latest/batch.html?utm_source=chatgpt.com "Running “Batch” Migrations for SQLite and Other Databases"
[6]: https://alembic.sqlalchemy.org/en/latest/autogenerate.html?utm_source=chatgpt.com "Auto Generating Migrations - Alembic's documentation!"
[7]: https://alembic.sqlalchemy.org/en/latest/ops.html?utm_source=chatgpt.com "Operation Reference — Alembic 1.18.4 documentation"
[8]: https://docs.sqlalchemy.org/en/latest/dialects/postgresql.html?utm_source=chatgpt.com "PostgreSQL — SQLAlchemy 2.1 Documentation"
[9]: https://docs.cloud.google.com/sql/docs/postgres?utm_source=chatgpt.com "Cloud SQL for PostgreSQL documentation"
[10]: https://docs.cloud.google.com/sql/docs/postgres/create-instance?utm_source=chatgpt.com "Create instances | Cloud SQL for PostgreSQL"
[11]: https://docs.cloud.google.com/sql/docs/postgres/connect-run?utm_source=chatgpt.com "Connect from Cloud Run | Cloud SQL for PostgreSQL"
[12]: https://docs.sqlalchemy.org/dialects/?utm_source=chatgpt.com "Dialects — SQLAlchemy 2.0 Documentation"

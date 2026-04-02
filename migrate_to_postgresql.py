import os
import sys
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), 'src')))

from db_service import User, Business, Transaction, ProcessedMessage, Base, get_engine

load_dotenv()

SQLITE_URL = "sqlite:///./help_u_bookkeeper.db"

# This will use the Connector if credentials are in .env
pg_engine = get_engine()
sqlite_engine = create_engine(SQLITE_URL)

TABLES_IN_ORDER = [
    User,
    Business,
    Transaction,
    ProcessedMessage
]

def copy_table(model, source_session: Session, target_session: Session):
    print(f"Migrating {model.__tablename__}...")
    rows = source_session.execute(select(model)).scalars().all()
    count = 0
    for row in rows:
        data = {
            c.name: getattr(row, c.name)
            for c in model.__table__.columns
        }
        # Check if record already exists in target to avoid duplicates
        pk_columns = [c.name for c in model.__table__.primary_key.columns]
        filter_kwargs = {pk: data[pk] for pk in pk_columns}
        
        exists = target_session.query(model).filter_by(**filter_kwargs).first()
        if not exists:
            target_session.add(model(**data))
            count += 1
    
    target_session.commit()
    print(f"Finished {model.__tablename__}. Added {count} new rows.")

def main():
    print("Starting data migration from SQLite to PostgreSQL...")
    
    # Create tables in PostgreSQL first if they don't exist
    print("Ensuring schema exists in PostgreSQL...")
    Base.metadata.create_all(bind=pg_engine)
    
    with Session(sqlite_engine) as source_session, Session(pg_engine) as target_session:
        for model in TABLES_IN_ORDER:
            try:
                copy_table(model, source_session, target_session)
            except Exception as e:
                print(f"Error migrating {model.__tablename__}: {e}")
                target_session.rollback()

    print("Migration completed successfully!")

if __name__ == "__main__":
    main()

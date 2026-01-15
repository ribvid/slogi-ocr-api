from sqlmodel import SQLModel, Session, create_engine
from pathlib import Path

# Create data directory if it doesn't exist
data_dir = Path("/code/data")
data_dir.mkdir(parents=True, exist_ok=True)

sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{data_dir / sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session

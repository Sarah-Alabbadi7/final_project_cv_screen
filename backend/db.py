# backend/db.py
import os
from sqlmodel import SQLModel, create_engine, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cv_screening.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)

def get_session() -> Session:
    # Used as: with get_session() as sess:
    return Session(engine)

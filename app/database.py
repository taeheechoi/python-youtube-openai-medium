import os
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine
from .config import get_config

config = get_config()
DATABASE_URL = config.DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={
    "check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
Base.metadata.create_all(bind=engine)

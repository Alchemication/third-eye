from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import DB_FILE_PATH
import sqlite3


LOG_DB_EVENTS = True

# Sql lite connection params, change connection params below to other DB for more production-ready code
engine = create_engine(f"sqlite:///{DB_FILE_PATH}", connect_args={"check_same_thread": False,
                                                                  "timeout": 15},  echo=LOG_DB_EVENTS)
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# for sharing thread-safe sessions: https://docs.sqlalchemy.org/en/14/orm/contextual.html
Session = scoped_session(session_factory)

Base = declarative_base()


def get_db_conn():
    return sqlite3.connect(DB_FILE_PATH, check_same_thread=False)

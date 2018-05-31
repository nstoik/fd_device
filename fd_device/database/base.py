from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

from ..settings import get_config

Base = declarative_base()

def get_engine():
    config = get_config()
    engine = create_engine(config.SQLALCHEMY_DATABASE_URI)
    return engine

def get_session():
    engine = get_engine()
    session = sessionmaker(bind=engine)
    db_session = scoped_session(session)

    return db_session()

def get_base(with_query=False):
    if with_query:
        # Adds Query Property to Models - enables `User.query.query_method()`
        db_session = get_session()
        Base.query = db_session.query_property()
    return Base


def create_all_tables():
    # Create Tables
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    return

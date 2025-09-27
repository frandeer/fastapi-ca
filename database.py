from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_settings

settings = get_settings()

SQLALCHEMY_DATABASE_URL = (
    "postgresql://"
    f"{settings.database_username}:{settings.database_password}"
    "@127.0.0.1:5432/fastapi_ca"
)
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

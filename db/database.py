from sqlmodel import Session
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel
from db import models


base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / ".env"


load_dotenv(dotenv_path=env_path)

database_url = os.getenv("DATABASE_URL")

if not database_url:
   
    raise ValueError("¡Error CRÍTICO! No se encontró la variable DATABASE_URL en el entorno ni en el .env.")


if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)
# -------------------------------------------

engine = create_engine(database_url)

def create_db_and_tables():

    from db import models 
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
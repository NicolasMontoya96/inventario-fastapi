from sqlmodel import Session
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel
from db import models

# Esto busca el archivo .env subiendo un nivel desde la carpeta 'db'
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / ".env"

load_dotenv(dotenv_path=env_path)

database_url = os.getenv("DATABASE_URL")

if not database_url:
    raise ValueError(f"No se encontró el .env en: {env_path}")

engine = create_engine(database_url)

def create_db_and_tables():
    # Asegúrate de importar tus modelos AQUÍ antes de llamar a create_all
    # para que SQLModel sepa qué tablas crear.
    from db import models 
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
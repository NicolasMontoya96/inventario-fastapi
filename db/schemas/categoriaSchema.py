from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional
from decimal import Decimal

class CategoriaBase(SQLModel):
    nombre: str = Field(index=True, unique=True) # "Relojes", "Perfumes", etc.
    descripcion: Optional[str] = None

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id: int

class CategoriaUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
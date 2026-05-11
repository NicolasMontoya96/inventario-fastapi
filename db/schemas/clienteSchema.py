from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional
from decimal import Decimal

class ClienteBase(SQLModel):
    nombre: str
    apellido: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    descripcion: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None)

class ClienteCreate(ClienteBase):
    pass

class ClienteResponse(ClienteBase):
    id: int

class ClienteUpdate(SQLModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[str] = None
    descripcion: Optional[str] = None
    telefono: Optional[str] = None


from sqlmodel import SQLModel, Field
from typing import Optional
from decimal import Decimal

# --- SCHEMAS PARA CLIENTE ---

class ClienteBase(SQLModel):
    nombre: str
    apellido: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    descripcion: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None)

class ClienteCreate(ClienteBase):
    pass
    # No incluimos saldo_deuda aquí. La base de datos lo iniciará en 0.0 automáticamente.

class ClienteResponse(ClienteBase):
    id: int
    saldo_deuda: Decimal 
    # Aquí SÍ lo incluimos. Así el frontend o Thunder Client mostrarán la deuda actual.

class ClienteUpdate(SQLModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    email: Optional[str] = None
    descripcion: Optional[str] = None
    telefono: Optional[str] = None
    # No incluimos saldo_deuda aquí. Las deudas solo se bajan con "Abonos" o suben con "Ventas a Crédito".

class AbonoCreate(SQLModel):
    cliente_id: int
    monto_pagado: Decimal
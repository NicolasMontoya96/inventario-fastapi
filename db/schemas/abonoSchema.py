from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel
from decimal import Decimal

# --- SCHEMAS PARA ABONOS ---

class AbonoBase(SQLModel):
    cliente_id: int
    monto_abonado: Decimal
    notas: Optional[str] = None

class AbonoCreate(AbonoBase):
    pass

class AbonoResponse(AbonoBase):
    id: int
    fecha: datetime
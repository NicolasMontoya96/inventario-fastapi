from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel


# --- SCHEMAS PARA ABONOS ---

class AbonoBase(SQLModel):
    cliente_id: int
    monto_abonado: float
    notas: Optional[str] = None

class AbonoCreate(AbonoBase):
    pass

class AbonoResponse(AbonoBase):
    id: int
    fecha: datetime
from sqlmodel import SQLModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime


class DetalleDevolucionCreate(SQLModel):
    detalle_venta_id: int
    producto_id: int
    cantidad: int
    precio_unitario: Decimal


class DevolucionCreate(SQLModel):
    venta_id: int
    motivo: str
    total_devolucion: Decimal
    items: List[DetalleDevolucionCreate]


class DetalleDevolucionResponse(SQLModel):
    id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal


class DevolucionResponse(SQLModel):
    id: int
    fecha: datetime
    venta_id: int
    motivo: str
    total_devolucion: Decimal
    detalles: List[DetalleDevolucionResponse] = []

    class Config:
        from_attributes = True
from sqlmodel import SQLModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class ItemCarrito(SQLModel):
    producto_id: int
    cantidad: int = Field(gt=0)

class PedidoWebCreate(SQLModel):
    nombre_cliente: str
    telefono_cliente: str
    email_cliente: Optional[str] = None
    direccion_envio: str
    acepta_tratamiento_datos: bool
    items: List[ItemCarrito]

class DetallePedidoWebResponse(SQLModel):
    id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal

class PedidoWebResponse(SQLModel):
    id: int
    fecha: datetime
    nombre_cliente: str
    telefono_cliente: str
    email_cliente: Optional[str] = None
    direccion_envio: str
    total_pedido: Decimal
    estado: str
    referencia_pago: str
    detalles: List[DetallePedidoWebResponse] = []

    class Config:
        from_attributes = True
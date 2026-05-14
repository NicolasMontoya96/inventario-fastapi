from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any, List
from decimal import Decimal
from .clienteSchema import ClienteCreate
from pydantic import BaseModel, model_validator
from datetime import datetime
from db.models import DetalleVenta


class VentaResponse(SQLModel):
    id: int
    fecha: datetime
    cliente_id: int
    total_venta: Decimal
    cuota_inicial: Decimal
    monto_en_deuda: Decimal
    es_credito: bool
    metodo_pago: str
    detalles: List[DetalleVenta] = []

class DetalleVentaCreate(SQLModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal

class VentaCreate(SQLModel):
    # Opción 1: El cliente ya existe
    cliente_id: Optional[int] = None 
    
    # Opción 2: Datos para crear un cliente nuevo en este instante
    cliente_nuevo: Optional[ClienteCreate] = None 
    
    es_credito: bool = False
    cuota_inicial: Decimal = Decimal("0.0")
    metodo_pago: str
    items: List[DetalleVentaCreate]

    # Validación de seguridad: debe venir uno de los dos
    @model_validator(mode="after")
    def verificar_cliente(self):
        if not self.cliente_id and not self.cliente_nuevo:
            raise ValueError("Debes proporcionar un cliente o los datos de cliente_nuevo")
        return self
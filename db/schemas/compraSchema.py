from typing import List, Optional
from decimal import Decimal
from datetime import datetime
from pydantic import model_validator
from db.models import DetalleCompra
from sqlmodel import SQLModel
from .proveedorSchema import ProveedorCreate 

# 1. LA PIEZA PEQUEÑA (Los productos que entran)
class DetalleCompraCreate(SQLModel):
    producto_id: int
    cantidad: int
    precio_compra: Decimal

# 2. LA CAJA GRANDE (El encabezado híbrido)
class CompraCreate(SQLModel):
    # Opción A: El proveedor ya existe
    proveedor_id: Optional[int] = None 
    
    # Opción B: Proveedor nuevo sobre la marcha
    proveedor_nuevo: Optional[ProveedorCreate] = None 
    
    numero_factura: str
    
    # La lista de productos que están ingresando
    items: List[DetalleCompraCreate]

    # Validación de seguridad: debe venir uno de los dos
    @model_validator(mode="after")
    def verificar_proveedor(self):
        if not self.proveedor_id and not self.proveedor_nuevo:
            raise ValueError("Debes proporcionar un proveedor o los datos de proveedor_nuevo")
        return self

class CompraResponse(SQLModel):
    id: int
    proveedor_id: int
    fecha: datetime
    numero_factura: str
    total: Decimal
    
    # Aquí es donde ocurre la magia relacional:
    # FastAPI buscará los detalles asociados a esta compra y los meterá en esta lista automáticamente
    detalles: List[DetalleCompra] = []
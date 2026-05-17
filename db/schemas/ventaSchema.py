from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any, List
from decimal import Decimal
from .clienteSchema import ClienteCreate
from pydantic import BaseModel, model_validator
from datetime import datetime
from db.models import DetalleVenta

class ClienteMin(SQLModel):
    nombre: str
    apellido: Optional[str] = None

# NUEVO: Esquema de salida para el detalle, asegurando la entrega de nombre_producto
class DetalleVentaResponse(SQLModel):
    id: Optional[int] = None
    venta_id: int
    producto_id: int
    nombre_producto: str = ""  # 👈 ESTA LÍNEA ES LA QUE LE DA PERMISO DE VIAJAR AL FRONTEND
    cantidad: int
    precio_unitario: Decimal

class VentaResponse(SQLModel):
    id: int
    fecha: datetime
    cliente_id: int
    total_venta: Decimal
    cuota_inicial: Decimal
    monto_en_deuda: Decimal
    es_credito: bool
    metodo_pago: str
    # MODIFICADO: Ahora usa el esquema de respuesta que no filtra el nombre
    detalles: List[DetalleVentaResponse] = []
    cliente: Optional[ClienteMin] = None

class DetalleVentaCreate(SQLModel):
    producto_id: int
    cantidad: int
    precio_unitario: Decimal
    nombre_producto: Optional[str] = ""  # NUEVO: Evita errores si el front no lo manda en el body

class VentaCreate(SQLModel):
    # Opción 1: El cliente ya existe
    cliente_id: Optional[int] = None 
    
    # Opción 2: Datos para crear un cliente nuevo en este instante
    cliente_nuevo: Optional[ClienteCreate] = None 
    
    es_credito: bool = False
    cuota_inicial: Decimal = Decimal("0.0")
    metodo_pago: str
    items: List[DetalleVentaCreate]
    
    # Campo opcional para habilitar el registro retroactivo
    fecha: Optional[datetime] = None 

    # Validación de seguridad: debe venir uno de los dos
    @model_validator(mode="after")
    def verificar_cliente(self):
        if not self.cliente_id and not self.cliente_nuevo:
            raise ValueError("Debes proporcionar un cliente o los datos de cliente_nuevo")
        return self
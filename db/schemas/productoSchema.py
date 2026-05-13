from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal

class ProductoBase(SQLModel):
    nombre: str = Field(min_length=3, max_length=100)
    descripcion: Optional[str] = None
    # Cambiado a Decimal para precisión total
    precio_venta: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0")) 
    stock: int = Field(default=0, ge=0)
    
    # El campo mágico para las variantes (Tallas, Colores, etc.)
    especificaciones: Dict[str, Any] = Field(default={}) 
    
    categoria_id: int
    proveedor_id: int

class ProductoCreate(ProductoBase):
    pass  

class ProductoList(SQLModel):
    id: int
    nombre: str
    precio_venta: Decimal # También aquí para el listado
    stock: int
    # En el listado podrías omitir las especificaciones para que sea más rápido

class ProductoResponse(ProductoBase):
    id: int 

    class Config:
        from_attributes = True 

class ProductoUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_venta: Optional[Decimal] = None # Consistencia con Decimal
    stock: Optional[int] = None
    especificaciones: Optional[Dict[str, Any]] = None # También se puede actualizar
    categoria_id: Optional[int] = None
    proveedor_id: Optional[int] = None
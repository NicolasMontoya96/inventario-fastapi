from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal

class ProductoBase(SQLModel):
    nombre: str = Field(min_length=3, max_length=100)
    descripcion: Optional[str] = None
    
    # 📝 MODIFICADO: Añadido precio_costo con consistencia Decimal para la Opción B
    precio_costo: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0")) 
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
    precio_costo: Decimal # MODIFICADO: Añadido aquí para que lo puedas ver/mapear en las tablas de listados
    precio_venta: Decimal 
    stock: int
    # 👇 ¡AÑADE ESTAS DOS LÍNEAS AQUÍ!
    categoria_id: int
    proveedor_id: int

class ProductoResponse(ProductoBase):
    id: int 

    class Config:
        from_attributes = True 

class ProductoUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_costo: Optional[Decimal] = None # MODIFICADO: Permitir actualizar el costo si cambia el distribuidor
    precio_venta: Optional[Decimal] = None 
    stock: Optional[int] = None
    especificaciones: Optional[Dict[str, Any]] = None 
    categoria_id: Optional[int] = None
    proveedor_id: Optional[int] = None
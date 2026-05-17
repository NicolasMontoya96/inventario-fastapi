from sqlmodel import SQLModel, Field
from typing import Optional, Dict, Any
from decimal import Decimal

class ProductoBase(SQLModel):
    nombre: str = Field(min_length=3, max_length=100)
    descripcion: Optional[str] = None
    precio_compra: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    precio_venta: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"))
    stock: int = Field(default=0, ge=0)
    especificaciones: Dict[str, Any] = Field(default={})
    categoria_id: int
    proveedor_id: int

class ProductoCreate(ProductoBase):
    pass

class ProductoList(SQLModel):
    id: int
    nombre: str
    precio_compra: Decimal
    precio_venta: Decimal
    stock: int
    categoria_id: int
    proveedor_id: int

class ProductoResponse(ProductoBase):
    id: int

    class Config:
        from_attributes = True

class ProductoUpdate(SQLModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_compra: Optional[Decimal] = None
    precio_venta: Optional[Decimal] = None
    stock: Optional[int] = None
    especificaciones: Optional[Dict[str, Any]] = None
    categoria_id: Optional[int] = None
    proveedor_id: Optional[int] = None
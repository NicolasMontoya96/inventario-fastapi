from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import Optional
from decimal import Decimal

# 1. BASE: Lo que es común a todos (Evita repetir código)
class ProductoBase(SQLModel):
    nombre: str = Field(min_length=3, max_length=100)
    descripcion: Optional[str] 
    precio_venta: float = Field(default=0.0, ge=0.0) # ge=0.0 asegura que no sea negativo
    stock: int = Field(default=0, ge=0)
    categoria_id: int
    proveedor_id: int # Esta es la llave que conecta con el proveedor


class ProductoCreate(ProductoBase):
    pass  


class ProductoList(SQLModel):
    id: int
    nombre: str
    precio_venta: float
    stock: int
    


# Lo que el sistema devuelve
class ProductoResponse(ProductoBase):
    id: int  # Aquí añadimos el ID generado por Postgres

    class Config:
        from_attributes = True # Esto es vital para que SQLModel convierta el objeto de DB a JSON


class ProductoUpdate(SQLModel):
   nombre: Optional[str] = None
   descripcion: Optional[str] = None
   precio_venta: Optional[float] = None
   stock: Optional[int] = None
   proveedor_id: Optional[int] = None
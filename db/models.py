from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

# --- TABLAS INDEPENDIENTES ---

class Usuario(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password_hash: str
    is_active: bool = Field(default=True)

class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    apellido: str
    email: Optional[str] = None
    descripcion: Optional[str] = None
    telefono: Optional[str] = None


class Proveedor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_empresa: Optional[str]
    nit: str = Field(unique=True)
    contacto: Optional[str] = None
    descripcion: Optional[str] = None

# --- TABLAS DEPENDIENTES ---

class Producto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: Optional[str] = None
    precio_venta: Decimal
    stock: int = Field(default=0)
    #Relación con Proveedor
    proveedor_id: int = Field(foreign_key="proveedor.id")

class Ventas(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime
    cliente_id: int = Field(foreign_key="cliente.id")
    total: Decimal
    metodo_pago: str

class DetalleVenta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.id")
    producto_id: int = Field(foreign_key="producto.id")
    cantidad: int
    precio_unitario: Decimal

class Compra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    proveedor_id: int = Field(foreign_key="proveedor.id")
    fecha: datetime
    numero_factura: str
    total: Decimal

class DetalleCompra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    compra_id: int = Field(foreign_key="compra.id")
    producto_id: int = Field(foreign_key="producto.id")
    cantidad: int
    precio_compra:Decimal

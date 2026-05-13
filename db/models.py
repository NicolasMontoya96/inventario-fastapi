from sqlmodel import Column, SQLModel,JSON, Field, Relationship
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
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
    nombre: str = Field(nullable=False)
    apellido: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)
    descripcion: Optional[str] = Field(default=None)
    telefono: Optional[str] = Field(default=None)
    
    # Cambiado a Decimal para que "hable el mismo idioma" que las ventas
    saldo_deuda: Decimal = Field(default=Decimal("0.0"))


class Proveedor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre_empresa: str
    nit: str = Field(unique=True)
    contacto: Optional[str] = None
    descripcion: Optional[str] = None

# --- TABLAS DEPENDIENTES ---
class Categoria(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True) 
    nombre: str = Field(unique=True, index=True)
    descripcion: Optional[str]


class Producto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: Optional[str] = None
    precio_venta: Decimal
    stock: int = Field(default=0)
    
    # Cambiado a JSONB para mejor rendimiento en Postgres
    especificaciones: dict = Field(default={}, sa_column=Column(JSONB))
    
    proveedor_id: int = Field(foreign_key="proveedor.id")
    categoria_id: int = Field(foreign_key="categoria.id")

class Ventas(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(default_factory=datetime.now)
    cliente_id: int = Field(foreign_key="cliente.id")
    
    
    total_venta: Decimal 
    cuota_inicial: Decimal = Field(default=0.0)
    monto_en_deuda: Decimal = Field(default=0.0) 
    
    es_credito: bool = Field(default=False)
    metodo_pago: str 

    
    detalles: list["DetalleVenta"] = Relationship(back_populates="venta")

class DetalleVenta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.id")
    producto_id: int = Field(foreign_key="producto.id")
    cantidad: int
    precio_unitario: Decimal

    # Relación inversa
    venta: "Ventas" = Relationship(back_populates="detalles")

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


class Abono(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(default_factory=datetime.now)
    cliente_id: int = Field(foreign_key="cliente.id")
    
    # Cambiado a Decimal para consistencia contable
    monto_abonado: Decimal = Field(default=Decimal("0.0"))
    notas: Optional[str] = Field(default=None)

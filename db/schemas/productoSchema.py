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
    imagen_url: Optional[str] = None          # <-- NUEVO
    # Controla si el producto se ve en la tienda pública, aparte de que ya
    # exista en el inventario. False por defecto: el admin lo activa a
    # propósito, nunca se publica solo.
    publicado_en_tienda: bool = False

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
    imagen_url: Optional[str] = None          # <-- NUEVO
    publicado_en_tienda: bool = False

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
    imagen_url: Optional[str] = None          # <-- NUEVO
    publicado_en_tienda: Optional[bool] = None


# --- Catálogo público (tienda) ---
# Deliberadamente NO hereda de ProductoBase: nunca debe llevar
# precio_compra (costo) ni proveedor_id — son datos internos del negocio,
# no algo que un cliente en internet deba poder consultar.
class ProductoCatalogoPublico(SQLModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    precio_venta: Decimal
    stock: int
    especificaciones: Dict[str, Any] = Field(default={})
    categoria_id: int
    imagen_url: Optional[str] = None

    class Config:
        from_attributes = True
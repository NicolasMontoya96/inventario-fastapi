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
    rol: str = Field(default="admin") 

class Cliente(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str = Field(nullable=False)
    apellido: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None, nullable=True)
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
    precio_compra: Decimal = Field(default=Decimal("0.0")) 
    precio_venta: Decimal
    stock: int = Field(default=0)
    especificaciones: dict = Field(default={}, sa_column=Column(JSONB))
    activo: bool = Field(default=True)
    proveedor_id: int = Field(foreign_key="proveedor.id")
    categoria_id: int = Field(foreign_key="categoria.id")
    imagen_url: Optional[str] = Field(default=None)
    # Separa "existe en el inventario" de "se muestra en la tienda online".
    # Por defecto false: nada se publica solo porque se registró en el
    # inventario — el admin lo activa a propósito cuando el producto ya
    # tiene foto, precio confirmado y está listo para vender en línea.
    publicado_en_tienda: bool = Field(default=False)

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
    cliente: Optional["Cliente"] = Relationship()

class DetalleVenta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    venta_id: int = Field(foreign_key="ventas.id")
    producto_id: int = Field(foreign_key="producto.id")
    cantidad: int
    precio_unitario: Decimal
    nombre_producto: str = Field(default="")

    # Relación inversa
    venta: "Ventas" = Relationship(back_populates="detalles")

class Compra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    proveedor_id: int = Field(foreign_key="proveedor.id")
    fecha: datetime
    numero_factura: str
    total: Decimal
    proveedor: Optional["Proveedor"] = Relationship()
    detalles: list["DetalleCompra"] = Relationship(back_populates="compra")


class DetalleCompra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    compra_id: int = Field(foreign_key="compra.id")
    producto_id: int = Field(foreign_key="producto.id")

    # Guardamos el nombre exacto del artículo al momento de la transacción
    nombre_producto: Optional[str] = Field(default=None, max_length=150)
    cantidad: int
    precio_compra: Decimal = Field(default=0, decimal_places=2)
    compra: "Compra" = Relationship(back_populates="detalles")
    


class Abono(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(default_factory=datetime.now)
    cliente_id: int = Field(foreign_key="cliente.id")
    
    monto_abonado: Decimal = Field(default=Decimal("0.0"))
    notas: Optional[str] = Field(default=None)


class Devolucion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(default_factory=datetime.now)
    venta_id: int = Field(foreign_key="ventas.id")
    motivo: str
    total_devolucion: Decimal

    detalles: list["DetalleDevolucion"] = Relationship(back_populates="devolucion")


class DetalleDevolucion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    devolucion_id: int = Field(foreign_key="devolucion.id")
    detalle_venta_id: int = Field(foreign_key="detalleventa.id")
    producto_id: int = Field(foreign_key="producto.id")
    nombre_producto: str = Field(default="")
    cantidad: int
    precio_unitario: Decimal

    devolucion: "Devolucion" = Relationship(back_populates="detalles")

#-----------------------------------------------------------------------
#Integración Web

class PedidoWeb(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fecha: datetime = Field(default_factory=datetime.now)

    nombre_cliente: str
    telefono_cliente: str
    email_cliente: Optional[str] = Field(default=None)
    # direccion_envio queda como el campo "crudo" por compatibilidad hacia
    # atrás (pedidos viejos solo tienen esto). Los pedidos nuevos llenan
    # además los campos de abajo, estructurados, para que el panel de admin
    # y las guías de envío no dependan de que el cliente haya escrito bien
    # la dirección en un solo cuadro de texto.
    direccion_envio: str
    departamento: Optional[str] = Field(default=None)
    ciudad: Optional[str] = Field(default=None)
    direccion: Optional[str] = Field(default=None)
    referencia_direccion: Optional[str] = Field(default=None)
    acepta_tratamiento_datos: bool = Field(default=False)

    total_pedido: Decimal
    estado: str = Field(default="pendiente")  # pendiente | pagado | fallido | expirado | enviado | entregado

    referencia_pago: str = Field(unique=True, index=True)
    transaccion_wompi_id: Optional[str] = Field(default=None, index=True)
    expira_en: Optional[datetime] = Field(default=None)

    # Se llenan a mano desde el panel de admin cuando se despacha el
    # pedido (estado -> "enviado"). Nunca los pone el cliente ni ninguna
    # transportadora automáticamente — por ahora no hay integración con
    # ninguna.
    transportadora: Optional[str] = Field(default=None)
    numero_guia: Optional[str] = Field(default=None)

    detalles: list["DetallePedidoWeb"] = Relationship(back_populates="pedido")


class DetallePedidoWeb(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pedido_id: int = Field(foreign_key="pedidoweb.id")
    producto_id: int = Field(foreign_key="producto.id")
    cantidad: int
    precio_unitario: Decimal
    nombre_producto: str = Field(default="")

    pedido: "PedidoWeb" = Relationship(back_populates="detalles")
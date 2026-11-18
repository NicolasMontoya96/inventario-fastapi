from sqlmodel import SQLModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from pydantic import field_serializer

class ItemCarrito(SQLModel):
    producto_id: int
    cantidad: int = Field(gt=0)

class PedidoWebCreate(SQLModel):
    nombre_cliente: str
    telefono_cliente: str
    email_cliente: Optional[str] = None
    direccion_envio: str
    acepta_tratamiento_datos: bool
    items: List[ItemCarrito]

class DetallePedidoWebResponse(SQLModel):
    id: int
    producto_id: int
    nombre_producto: str
    cantidad: int
    precio_unitario: Decimal

class PedidoWebResponse(SQLModel):
    id: int
    fecha: datetime
    nombre_cliente: str
    telefono_cliente: str
    email_cliente: Optional[str] = None
    direccion_envio: str
    total_pedido: Decimal
    estado: str
    referencia_pago: str
    # Ya existía en el modelo (se usa para liberar el stock reservado),
    # simplemente no se exponía todavía. El frontend la necesita para
    # mostrar la cuenta regresiva en la página de "pedido pendiente".
    expira_en: Optional[datetime] = None
    detalles: List[DetallePedidoWebResponse] = []

    class Config:
        from_attributes = True

    # El modelo guarda estas fechas con datetime.now() SIN zona horaria,
    # pero el servidor (Railway) corre en UTC — ese valor "naive" ya es UTC.
    # Si se lo mandamos así al navegador, el navegador lo interpreta como
    # SU PROPIA hora local (no UTC) en vez de UTC, y la cuenta regresiva en
    # la pantalla de "pedido pendiente" aparece corrida por el desfase de
    # zona horaria del cliente (ej. 5 horas de más en Colombia). Marcarla
    # explícitamente como UTC aquí lo corrige sin tocar cómo se guarda en
    # la base de datos ni requerir una migración.
    @field_serializer("fecha", "expira_en")
    def _marcar_como_utc(self, valor: Optional[datetime]) -> Optional[datetime]:
        if valor is not None and valor.tzinfo is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor
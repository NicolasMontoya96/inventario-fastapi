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
    # Dirección estructurada en vez de un solo cuadro de texto libre — más
    # fácil de usar para una guía de envío y de mostrar en el panel de
    # admin. direccion_envio (el texto combinado, para compatibilidad con
    # código viejo que todavía lo lee) se arma solo en el backend a partir
    # de estos campos, no lo manda el frontend.
    departamento: str
    ciudad: str
    direccion: str
    referencia_direccion: Optional[str] = None
    acepta_tratamiento_datos: bool
    items: List[ItemCarrito]

class MarcarEnviadoRequest(SQLModel):
    # Ambos opcionales: a veces se despacha sin número de guía a mano
    # (ej. entrega personal), y no queremos bloquear el cambio de estado
    # por eso.
    transportadora: Optional[str] = None
    numero_guia: Optional[str] = None


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
    departamento: Optional[str] = None
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    referencia_direccion: Optional[str] = None
    total_pedido: Decimal
    estado: str
    referencia_pago: str
    transportadora: Optional[str] = None
    numero_guia: Optional[str] = None
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
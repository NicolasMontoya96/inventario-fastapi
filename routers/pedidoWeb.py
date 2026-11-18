import os
import hashlib
import uuid
import resend
from datetime import datetime, timedelta

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select, update

from db.models import PedidoWeb, DetallePedidoWeb, Producto
from db.schemas.pedidoWebSchema import PedidoWebCreate, PedidoWebResponse
from db.database import get_session
from limiter import limiter
from auth.auth import obtener_usuario_actual

resend.api_key = os.getenv("RESEND_API_KEY")

router = APIRouter(prefix="/pedidos-web", tags=["Pedidos Web"])


MINUTOS_RESERVA = 15


def liberar_pedidos_vencidos(session: Session):
    """Antes de crear un pedido nuevo, libera el stock de pedidos pendientes
    que ya vencieron (nadie completó el pago a tiempo)."""
    vencidos = session.exec(
        select(PedidoWeb).where(
            PedidoWeb.estado == "pendiente",
            PedidoWeb.expira_en < datetime.now(),
        )
    ).all()
    for pedido in vencidos:
        for detalle in pedido.detalles:
            db_producto = session.get(Producto, detalle.producto_id)
            if db_producto:
                db_producto.stock += detalle.cantidad
                session.add(db_producto)
        pedido.estado = "expirado"
        session.add(pedido)
    if vencidos:
        session.commit()


def liberar_si_vencido(session: Session, pedido: PedidoWeb) -> PedidoWeb:
    """Mismo chequeo que liberar_pedidos_vencidos() pero para un pedido
    puntual, al momento de consultarlo. Sin esto, un pedido vencido se queda
    viendo "pendiente" para el cliente que lo consulta hasta que OTRO
    cliente complete un pedido nuevo y dispare el barrido general — con la
    cuenta regresiva del frontend, eso se nota de inmediato."""
    if pedido.estado == "pendiente" and pedido.expira_en and pedido.expira_en < datetime.now():
        for detalle in pedido.detalles:
            db_producto = session.get(Producto, detalle.producto_id)
            if db_producto:
                db_producto.stock += detalle.cantidad
                session.add(db_producto)
        pedido.estado = "expirado"
        session.add(pedido)
        session.commit()
        session.refresh(pedido)
    return pedido


def enviar_correo_confirmacion_pedido(pedido: PedidoWeb):
    if not pedido.email_cliente:
        return
    try:
        filas_html = "".join(
            f"<tr><td>{d.nombre_producto}</td><td>{d.cantidad}</td><td>${d.precio_unitario:,.0f}</td></tr>"
            for d in pedido.detalles
        )
        resend.Emails.send({
            "from": "M Accesorios <onboarding@resend.dev>",
            "to": pedido.email_cliente,
            "subject": f"Recibimos tu pedido #{pedido.id} — M Accesorios",
            "html": f"""
                <h2>¡Gracias por tu pedido, {pedido.nombre_cliente}!</h2>
                <p>Reservamos tus productos por <strong>15 minutos</strong> mientras completas el pago.</p>
                <p><strong>Referencia de pago:</strong> {pedido.referencia_pago}</p>
                <table border="1" cellpadding="6" style="border-collapse:collapse">
                    <tr><th>Producto</th><th>Cantidad</th><th>Precio</th></tr>
                    {filas_html}
                </table>
                <p><strong>Total: ${pedido.total_pedido:,.0f}</strong></p>
                <p>Dirección de envío: {pedido.direccion_envio}</p>
            """,
        })
    except Exception as error_correo:
        print(f"Alerta del Sistema: No se pudo enviar el correo de confirmación del pedido {pedido.id}: {error_correo}")


@router.post("/", response_model=PedidoWebResponse, status_code=201)
@limiter.limit("5/minute")
def crear_pedido(request: Request, pedido_data: PedidoWebCreate, session: Session = Depends(get_session)):
    if not pedido_data.items:
        raise HTTPException(status_code=400, detail="El pedido no tiene productos")

    if not pedido_data.acepta_tratamiento_datos:
        raise HTTPException(
            status_code=400,
            detail="Debes aceptar el tratamiento de datos personales para continuar",
        )

    liberar_pedidos_vencidos(session)

    total = 0
    detalles_a_crear = []

    for item in pedido_data.items:
        db_producto = session.get(Producto, item.producto_id)
        if not db_producto or not db_producto.activo:
            raise HTTPException(status_code=404, detail=f"Producto {item.producto_id} no encontrado")

        # RESERVA ATÓMICA: si dos personas compran lo mismo a la vez,
        # solo una gana — la base de datos lo garantiza, no el código.
        resultado = session.exec(
            update(Producto)
            .where(Producto.id == item.producto_id, Producto.stock >= item.cantidad)
            .values(stock=Producto.stock - item.cantidad)
        )
        if resultado.rowcount == 0:
            raise HTTPException(
                status_code=409,
                detail=f"'{db_producto.nombre}' ya no tiene suficiente stock disponible",
            )

        subtotal = db_producto.precio_venta * item.cantidad
        total += subtotal
        detalles_a_crear.append(
            DetallePedidoWeb(
                producto_id=db_producto.id,
                cantidad=item.cantidad,
                precio_unitario=db_producto.precio_venta,
                nombre_producto=db_producto.nombre,
            )
        )

    nuevo_pedido = PedidoWeb(
        nombre_cliente=pedido_data.nombre_cliente,
        telefono_cliente=pedido_data.telefono_cliente,
        email_cliente=pedido_data.email_cliente,
        direccion_envio=pedido_data.direccion_envio,
        acepta_tratamiento_datos=pedido_data.acepta_tratamiento_datos,
        total_pedido=total,
        referencia_pago=str(uuid.uuid4()),
        expira_en=datetime.now() + timedelta(minutes=MINUTOS_RESERVA),
    )
    session.add(nuevo_pedido)
    session.commit()
    session.refresh(nuevo_pedido)

    for detalle in detalles_a_crear:
        detalle.pedido_id = nuevo_pedido.id
        session.add(detalle)
    session.commit()
    session.refresh(nuevo_pedido)

    enviar_correo_confirmacion_pedido(nuevo_pedido)
    return nuevo_pedido


@router.get("/", response_model=list[PedidoWebResponse], dependencies=[Depends(obtener_usuario_actual)])
def listar_pedidos(
    estado: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Listado para el panel de administración (protegido). El cliente de
    la tienda nunca llega aquí: solo conoce su propia referencia de pago."""
    consulta = select(PedidoWeb).order_by(PedidoWeb.fecha.desc())
    if estado:
        consulta = consulta.where(PedidoWeb.estado == estado)
    return session.exec(consulta).all()


@router.get("/{referencia_pago}", response_model=PedidoWebResponse)
def consultar_pedido(referencia_pago: str, session: Session = Depends(get_session)):
    pedido = session.exec(
        select(PedidoWeb).where(PedidoWeb.referencia_pago == referencia_pago)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return liberar_si_vencido(session, pedido)


@router.get("/{referencia_pago}/firma-pago")
def obtener_firma_pago(referencia_pago: str, session: Session = Depends(get_session)):
    """Datos que el frontend necesita para abrir el Widget de Wompi sobre
    este pedido: llave pública (segura de compartir) + firma de integridad
    (prueba de que el monto/referencia no se manipularon en el navegador).

    El WOMPI_INTEGRITY_SECRET nunca sale de este endpoint — si saliera,
    cualquiera podría firmar un monto distinto al que realmente se debe."""
    pedido = session.exec(
        select(PedidoWeb).where(PedidoWeb.referencia_pago == referencia_pago)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    pedido = liberar_si_vencido(session, pedido)
    if pedido.estado != "pendiente":
        raise HTTPException(
            status_code=409,
            detail=f"Este pedido ya no admite pago (estado actual: {pedido.estado})",
        )

    llave_publica = os.getenv("WOMPI_PUBLIC_KEY")
    secreto_integridad = os.getenv("WOMPI_INTEGRITY_SECRET")
    if not llave_publica or not secreto_integridad:
        raise HTTPException(
            status_code=503,
            detail="Los pagos en línea todavía no están configurados. Intenta más tarde.",
        )

    moneda = "COP"
    # Wompi trabaja en centavos. Con Decimal evitamos el redondeo flotante
    # de float antes de pasar a entero (ej. 29990.0 * 100 puede dar
    # 2998999.9999... en binario y truncar mal con int()).
    monto_centavos = int((pedido.total_pedido * 100).to_integral_value())

    cadena_a_firmar = f"{referencia_pago}{monto_centavos}{moneda}{secreto_integridad}"
    firma = hashlib.sha256(cadena_a_firmar.encode()).hexdigest()

    return {
        "llave_publica": llave_publica,
        "referencia": referencia_pago,
        "monto_centavos": monto_centavos,
        "moneda": moneda,
        "firma_integridad": firma,
    }


@router.post("/webhook-wompi")
@limiter.limit("30/minute")
async def webhook_wompi(request: Request, session: Session = Depends(get_session)):
    payload = await request.json()

    firma = payload.get("signature", {})
    propiedades = firma.get("properties", [])
    # El timestamp viene en la raíz del payload, no dentro de "signature"
    # (ahí solo vienen "checksum" y "properties") — Wompi lo documenta así,
    # y es parte de la cadena que se firma.
    timestamp = payload.get("timestamp")
    checksum_recibido = firma.get("checksum", "")

    def obtener_valor(ruta: str):
        partes = ruta.split(".")
        valor = payload.get("data", {})
        for parte in partes:
            valor = valor.get(parte, {}) if isinstance(valor, dict) else None
        return valor

    cadena = "".join(str(obtener_valor(p)) for p in propiedades)
    cadena += str(timestamp)
    cadena += os.getenv("WOMPI_EVENTS_SECRET", "")

    checksum_calculado = hashlib.sha256(cadena.encode()).hexdigest().upper()

    if checksum_calculado != checksum_recibido.upper():
        raise HTTPException(status_code=401, detail="Firma inválida")

    transaccion = payload.get("data", {}).get("transaction", {})
    referencia = transaccion.get("reference")
    estado_wompi = transaccion.get("status")  # APPROVED | DECLINED | ERROR | VOIDED

    pedido = session.exec(
        select(PedidoWeb).where(PedidoWeb.referencia_pago == referencia)
    ).first()
    if not pedido:
        return {"ok": True}  # evento de un pedido que no conocemos, se ignora

    # Idempotencia: si Wompi reenvía el mismo evento, no se procesa dos veces
    if pedido.estado != "pendiente":
        return {"ok": True}

    pedido.transaccion_wompi_id = transaccion.get("id")

    if estado_wompi == "APPROVED":
        pedido.estado = "pagado"
    else:
        pedido.estado = "fallido"
        # el pago no se completó: devolvemos el stock reservado
        for detalle in pedido.detalles:
            db_producto = session.get(Producto, detalle.producto_id)
            if db_producto:
                db_producto.stock += detalle.cantidad
                session.add(db_producto)

    session.add(pedido)
    session.commit()
    return {"ok": True}
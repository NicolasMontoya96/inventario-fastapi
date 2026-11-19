import os
import hashlib
import secrets
import resend
from pathlib import Path
from datetime import datetime, timedelta

from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select, update

from db.models import PedidoWeb, DetallePedidoWeb, Producto
from db.schemas.pedidoWebSchema import PedidoWebCreate, PedidoWebResponse, MarcarEnviadoRequest
from db.database import get_session
from limiter import limiter
from auth.auth import obtener_usuario_actual

resend.api_key = os.getenv("RESEND_API_KEY")

router = APIRouter(prefix="/pedidos-web", tags=["Pedidos Web"])

# Logo para el encabezado de los correos, embebido como adjunto "inline"
# (referenciado con cid: en el HTML) en vez de cargarlo desde una URL
# pública — así funciona aunque la tienda todavía no esté publicada en un
# dominio real, y no depende de que ese dominio seguro siga existiendo.
_RUTA_LOGO_CORREO = Path(__file__).resolve().parent.parent / "assets" / "logo-correo.png"
_LOGO_CORREO_BYTES: Optional[bytes] = None
try:
    _LOGO_CORREO_BYTES = _RUTA_LOGO_CORREO.read_bytes()
except FileNotFoundError:
    # Si por lo que sea el archivo no está, seguimos sin el logo en vez de
    # que fallen los correos — no vale la pena tumbar un aviso de pedido
    # por un logo.
    pass

# HTML del encabezado del correo: el logo real si lo pudimos cargar, o si
# no (ambiente sin el archivo, por ejemplo) el wordmark de texto que se
# usaba antes — nunca dejamos el encabezado vacío.
if _LOGO_CORREO_BYTES:
    _LOGO_HTML = (
        '<img src="cid:logo-correo" width="64" height="64" alt="M Accesorios" '
        'style="display:block;margin:0 auto;border-radius:50%;">'
    )
else:
    _LOGO_HTML = (
        '<span style="font-size:18px;font-weight:800;letter-spacing:0.02em;'
        'color:#111111;">M &middot; Accesorios</span>'
    )

# Adjunto "inline" con el logo, referenciado en el HTML con cid:logo-correo.
# Resend espera el contenido como lista de bytes (no base64), según su
# propio ejemplo en Python. Lista vacía si no hay logo, para no mandar un
# adjunto vacío sin sentido.
_ADJUNTOS_LOGO = (
    [{
        "filename": "logo-correo.png",
        "content": list(_LOGO_CORREO_BYTES),
        "content_id": "logo-correo",
        "content_type": "image/png",
    }]
    if _LOGO_CORREO_BYTES
    else []
)


MINUTOS_RESERVA = 15

# Sin 0/O, 1/I/L — se prestan a confusión cuando alguien lee el código en
# voz alta o lo escribe a mano (ej. por WhatsApp).
_ALFABETO_REFERENCIA = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generar_referencia_pago(session: Session) -> str:
    """Código corto para que el cliente lo use de referencia (antes era un
    UUID completo de 36 caracteres — impráctico para leer, escribir a mano
    o decir por teléfono). No tiene ningún significado especial para Wompi
    ni para el resto del sistema: solo necesita ser único, y en cualquier
    parte donde antes se esperaba el UUID, este código funciona igual
    porque siempre se trata como texto simple, nunca se valida su formato."""
    for _ in range(5):
        codigo = "".join(secrets.choice(_ALFABETO_REFERENCIA) for _ in range(6))
        referencia = f"MA-{codigo}"
        ya_existe = session.exec(
            select(PedidoWeb).where(PedidoWeb.referencia_pago == referencia)
        ).first()
        if not ya_existe:
            return referencia
    # Si por una casualidad enorme las 5 veces chocaron con una referencia
    # existente, usamos algo con muchísima más entropía en vez de seguir
    # intentando — esto nunca debería pasar en la práctica.
    return f"MA-{secrets.token_hex(6).upper()}"


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


def _filas_html_detalles(pedido: PedidoWeb) -> str:
    filas = []
    for d in pedido.detalles:
        subtotal = d.cantidad * d.precio_unitario
        filas.append(f"""
            <tr>
                <td style="padding:12px 0;border-bottom:1px solid #EFEFEF;color:#111111;font-size:14px;">{d.nombre_producto}</td>
                <td style="padding:12px 0;border-bottom:1px solid #EFEFEF;color:#6A6A6A;font-size:14px;text-align:center;">{d.cantidad}</td>
                <td style="padding:12px 0;border-bottom:1px solid #EFEFEF;color:#111111;font-size:14px;text-align:right;font-weight:600;">${subtotal:,.0f}</td>
            </tr>
        """)
    return "".join(filas)


def _direccion_html(pedido: PedidoWeb) -> str:
    """Igual que en el panel de admin: si el pedido tiene los campos
    estructurados nuevos los usamos, y si no (pedidos de antes de ese
    cambio) caemos al texto combinado viejo."""
    if pedido.direccion:
        lineas = [pedido.direccion]
        if pedido.referencia_direccion:
            lineas.append(pedido.referencia_direccion)
        lineas.append(f"{pedido.ciudad}, {pedido.departamento}")
        return "<br>".join(lineas)
    return pedido.direccion_envio


def _bloque_guia_html(pedido: PedidoWeb) -> str:
    """Bloque opcional con transportadora/número de guía, solo para el
    correo de "pedido enviado" — y solo si se llenó al menos uno de los
    dos datos (se puede despachar sin número de guía, ej. entrega
    personal)."""
    if not pedido.transportadora and not pedido.numero_guia:
        return ""
    lineas = []
    if pedido.transportadora:
        lineas.append(pedido.transportadora)
    if pedido.numero_guia:
        lineas.append(f"Guía: {pedido.numero_guia}")
    return f"""
        <tr>
            <td style="padding:0 32px 8px 32px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#EFF6FF;border-radius:12px;">
                    <tr>
                        <td style="padding:16px 20px;">
                            <div style="font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#2563EB;margin-bottom:4px;">Datos de envío</div>
                            <div class="direccion-correo" style="font-size:14px;line-height:1.6;color:#111111;">{" &middot; ".join(lineas)}</div>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    """


def _plantilla_correo_pedido(
    pedido: PedidoWeb,
    *,
    etiqueta_insignia: str,
    color_insignia: str,
    color_texto_insignia: str,
    titulo: str,
    mensaje: str,
    bloque_extra: str = "",
) -> str:
    """Plantilla compartida por los correos de pedidos web (recibido / pago
    confirmado / enviado) — misma estructura, solo cambian la insignia de
    estado, el título, el mensaje y opcionalmente un bloque extra (ej. datos
    de envío). Todo con estilos inline y layout de tablas (no flexbox/grid)
    porque así es como hay que escribir HTML de correos para que se vea
    igual en Gmail, Outlook y el resto de clientes de correo."""
    return f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <!-- Sin esto, Gmail y sobre todo Apple Mail "autodetectan" la
        dirección de envío y la muestran subrayada y azul como si fuera un
        link (igual hacen con teléfonos y fechas) — no es nada que nuestro
        HTML esté generando, es el cliente de correo metiendo mano. -->
        <meta name="format-detection" content="telephone=no, date=no, address=no, email=no">
        <!-- El meta de arriba solo lo respeta Apple Mail. Gmail (web y
        app) detecta direcciones por su cuenta y las envuelve en su propio
        link azul hacia Google Maps, sin importar el meta tag — esta regla
        sobreescribe el estilo que Gmail le pone a ESE link específico
        (identificado por la clase que ponemos abajo en el texto de la
        dirección), sin tocar links reales que sí querramos mantener
        azules en otro lado del correo. -->
        <style type="text/css">
            .direccion-correo a {{
                color: #111111 !important;
                text-decoration: none !important;
                border-bottom: none !important;
                cursor: default !important;
            }}
        </style>
    </head>
    <body style="margin:0;padding:0;background-color:#F4F4F4;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F4F4F4;padding:32px 16px;">
            <tr>
                <td align="center">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background-color:#FFFFFF;border-radius:16px;overflow:hidden;">

                        <!-- Encabezado -->
                        <tr>
                            <td style="padding:28px 32px 24px 32px;text-align:center;border-bottom:1px solid #F0F0F0;">
                                {_LOGO_HTML}
                            </td>
                        </tr>

                        <!-- Insignia de estado + titulo -->
                        <tr>
                            <td style="padding:28px 32px 8px 32px;text-align:center;">
                                <span style="display:inline-block;padding:6px 14px;border-radius:999px;background-color:{color_insignia};color:{color_texto_insignia};font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;">{etiqueta_insignia}</span>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:8px 32px 4px 32px;text-align:center;">
                                <h1 style="margin:0;font-size:22px;font-weight:800;color:#111111;">{titulo}</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding:0 32px 24px 32px;text-align:center;">
                                <p style="margin:0;font-size:14px;line-height:1.6;color:#6A6A6A;">{mensaje}</p>
                            </td>
                        </tr>

                        <!-- Codigo de referencia -->
                        <tr>
                            <td style="padding:0 32px 24px 32px;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F7F7F7;border-radius:12px;">
                                    <tr>
                                        <td style="padding:16px 20px;text-align:center;">
                                            <div style="font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#9A9A9A;margin-bottom:4px;">Referencia de tu pedido</div>
                                            <div style="font-size:20px;font-weight:800;color:#111111;letter-spacing:0.03em;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;">{pedido.referencia_pago}</div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Detalle del pedido -->
                        <tr>
                            <td style="padding:0 32px;">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding:0 0 8px 0;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#9A9A9A;border-bottom:2px solid #111111;">Producto</td>
                                        <td style="padding:0 0 8px 0;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#9A9A9A;border-bottom:2px solid #111111;text-align:center;">Cant.</td>
                                        <td style="padding:0 0 8px 0;font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#9A9A9A;border-bottom:2px solid #111111;text-align:right;">Subtotal</td>
                                    </tr>
                                    {_filas_html_detalles(pedido)}
                                    <tr>
                                        <td style="padding:14px 0 0 0;"></td>
                                        <td style="padding:14px 0 0 0;font-size:14px;font-weight:700;color:#111111;text-align:right;">Total</td>
                                        <td style="padding:14px 0 0 0;font-size:18px;font-weight:800;color:#111111;text-align:right;">${pedido.total_pedido:,.0f}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Direccion de envio -->
                        <tr>
                            <td style="padding:28px 32px 8px 32px;">
                                <div style="font-size:11px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;color:#9A9A9A;margin-bottom:6px;">Dirección de envío</div>
                                <div class="direccion-correo" style="font-size:14px;line-height:1.6;color:#111111;">{_direccion_html(pedido)}</div>
                            </td>
                        </tr>
                        {bloque_extra}

                        <!-- Pie -->
                        <tr>
                            <td style="padding:28px 32px 32px 32px;">
                                <p style="margin:0;font-size:12px;line-height:1.6;color:#9A9A9A;text-align:center;">Guarda esta referencia por si necesitas contactarnos sobre tu pedido.</p>
                            </td>
                        </tr>
                    </table>

                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
                        <tr>
                            <td style="padding:20px 32px;text-align:center;">
                                <p style="margin:0;font-size:12px;color:#B0B0B0;">M Accesorios &middot; Cali, Colombia</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def enviar_correo_confirmacion_pedido(pedido: PedidoWeb):
    """Aviso de que el pedido se creó y quedó reservado — se envía al crear
    el pedido, ANTES de que el cliente pague. No confirma que el pago fue
    exitoso (por eso el texto habla de "reserva" y "completa el pago"), y se
    envía igual aunque el pago después falle o se venza la reserva. La
    confirmación real de compra es enviar_correo_pago_confirmado(), que solo
    se dispara cuando el webhook de Wompi aprueba el pago."""
    if not pedido.email_cliente:
        return
    try:
        resend.Emails.send({
            "from": "M Accesorios <onboarding@resend.dev>",
            "to": pedido.email_cliente,
            "subject": f"Recibimos tu pedido #{pedido.id} — M Accesorios",
            "html": _plantilla_correo_pedido(
                pedido,
                etiqueta_insignia="Pedido recibido",
                color_insignia="#FEF3E7",
                color_texto_insignia="#B45309",
                titulo=f"¡Gracias por tu pedido, {pedido.nombre_cliente}!",
                mensaje="Reservamos tus productos por 15 minutos mientras completas el pago. Pasado ese tiempo, el stock se libera.",
            ),
            "attachments": _ADJUNTOS_LOGO,
        })
    except Exception as error_correo:
        print(f"Alerta del Sistema: No se pudo enviar el correo de recepción del pedido {pedido.id}: {error_correo}")


def enviar_correo_pago_confirmado(pedido: PedidoWeb):
    """Confirmación real de compra: solo se llama desde el webhook de
    Wompi, cuando el pago quedó APROBADO de verdad. Si el pago falla o la
    reserva se vence, este correo nunca se envía."""
    if not pedido.email_cliente:
        return
    try:
        resend.Emails.send({
            "from": "M Accesorios <onboarding@resend.dev>",
            "to": pedido.email_cliente,
            "subject": f"¡Pago confirmado! Pedido #{pedido.id} — M Accesorios",
            "html": _plantilla_correo_pedido(
                pedido,
                etiqueta_insignia="Pago confirmado",
                color_insignia="#E3F7E9",
                color_texto_insignia="#15803D",
                titulo=f"¡Tu pago fue confirmado, {pedido.nombre_cliente}!",
                mensaje="Ya estamos preparando tu pedido para enviarlo.",
            ),
            "attachments": _ADJUNTOS_LOGO,
        })
    except Exception as error_correo:
        print(f"Alerta del Sistema: No se pudo enviar el correo de pago confirmado del pedido {pedido.id}: {error_correo}")


def enviar_correo_pedido_enviado(pedido: PedidoWeb):
    """Aviso de que el pedido salió hacia el cliente — se llama solo desde
    el endpoint de admin que marca el pedido como "enviado". Incluye
    transportadora/número de guía si se cargaron al momento de despachar."""
    if not pedido.email_cliente:
        return
    try:
        resend.Emails.send({
            "from": "M Accesorios <onboarding@resend.dev>",
            "to": pedido.email_cliente,
            "subject": f"¡Tu pedido va en camino! Pedido #{pedido.id} — M Accesorios",
            "html": _plantilla_correo_pedido(
                pedido,
                etiqueta_insignia="Pedido enviado",
                color_insignia="#DBEAFE",
                color_texto_insignia="#1D4ED8",
                titulo=f"¡Tu pedido va en camino, {pedido.nombre_cliente}!",
                mensaje="Ya despachamos tu pedido. Pronto debería llegar a la dirección que nos diste.",
                bloque_extra=_bloque_guia_html(pedido),
            ),
            "attachments": _ADJUNTOS_LOGO,
        })
    except Exception as error_correo:
        print(f"Alerta del Sistema: No se pudo enviar el correo de pedido enviado del pedido {pedido.id}: {error_correo}")


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

    # direccion_envio es el texto combinado que usan los correos y el
    # código viejo — se arma aquí a partir de los campos estructurados que
    # realmente llena el formulario, para no tener dos fuentes de verdad.
    partes_direccion = [pedido_data.direccion]
    if pedido_data.referencia_direccion:
        partes_direccion.append(pedido_data.referencia_direccion)
    partes_direccion.append(pedido_data.ciudad)
    partes_direccion.append(pedido_data.departamento)
    direccion_envio_combinada = ", ".join(p.strip() for p in partes_direccion if p and p.strip())

    nuevo_pedido = PedidoWeb(
        nombre_cliente=pedido_data.nombre_cliente,
        telefono_cliente=pedido_data.telefono_cliente,
        email_cliente=pedido_data.email_cliente,
        direccion_envio=direccion_envio_combinada,
        departamento=pedido_data.departamento,
        ciudad=pedido_data.ciudad,
        direccion=pedido_data.direccion,
        referencia_direccion=pedido_data.referencia_direccion,
        acepta_tratamiento_datos=pedido_data.acepta_tratamiento_datos,
        total_pedido=total,
        referencia_pago=generar_referencia_pago(session),
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

    if pedido.estado == "pagado":
        session.refresh(pedido)
        enviar_correo_pago_confirmado(pedido)

    return {"ok": True}


@router.post(
    "/{referencia_pago}/enviar",
    response_model=PedidoWebResponse,
    dependencies=[Depends(obtener_usuario_actual)],
)
def marcar_pedido_enviado(
    referencia_pago: str,
    datos: MarcarEnviadoRequest,
    session: Session = Depends(get_session),
):
    """Protegido (panel de admin): se llama cuando el pedido ya se empacó y
    se despachó. transportadora/numero_guia son opcionales — a veces se
    despacha sin ellos (ej. entrega personal)."""
    pedido = session.exec(
        select(PedidoWeb).where(PedidoWeb.referencia_pago == referencia_pago)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado != "pagado":
        raise HTTPException(
            status_code=409,
            detail=f"Solo se puede marcar como enviado un pedido pagado (estado actual: {pedido.estado})",
        )

    pedido.estado = "enviado"
    pedido.transportadora = datos.transportadora
    pedido.numero_guia = datos.numero_guia
    session.add(pedido)
    session.commit()
    session.refresh(pedido)

    enviar_correo_pedido_enviado(pedido)
    return pedido


@router.post(
    "/{referencia_pago}/entregar",
    response_model=PedidoWebResponse,
    dependencies=[Depends(obtener_usuario_actual)],
)
def marcar_pedido_entregado(referencia_pago: str, session: Session = Depends(get_session)):
    """Protegido (panel de admin): último paso del seguimiento, sin datos
    adicionales ni correo — solo refleja que el cliente ya recibió el
    pedido."""
    pedido = session.exec(
        select(PedidoWeb).where(PedidoWeb.referencia_pago == referencia_pago)
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    if pedido.estado != "enviado":
        raise HTTPException(
            status_code=409,
            detail=f"Solo se puede marcar como entregado un pedido enviado (estado actual: {pedido.estado})",
        )

    pedido.estado = "entregado"
    session.add(pedido)
    session.commit()
    session.refresh(pedido)
    return pedido
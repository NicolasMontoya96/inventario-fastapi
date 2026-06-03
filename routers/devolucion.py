from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from typing import List
from decimal import Decimal
from datetime import datetime

from db.database import get_session
from db.models import Devolucion, DetalleDevolucion, DetalleVenta, Ventas, Producto, Cliente
from db.schemas.devolucionSchema import DevolucionCreate, DevolucionResponse

router = APIRouter(
    prefix="/devoluciones",
    tags=["devoluciones"]
)


@router.get("/", response_model=List[DevolucionResponse])
def obtener_devoluciones(session: Session = Depends(get_session)):
    """Historial completo de devoluciones, más recientes primero."""
    return session.exec(select(Devolucion).order_by(Devolucion.fecha.desc())).all()


@router.post("/", response_model=DevolucionResponse, status_code=201)
def registrar_devolucion(data: DevolucionCreate, session: Session = Depends(get_session)):
    """
    Registra una devolución. Por cada item:
    - Revierte el stock del producto
    - Si la venta era a crédito, reduce la deuda del cliente
    """

    # 1. VALIDAR QUE LA VENTA EXISTE
    db_venta = session.get(Ventas, data.venta_id)
    if not db_venta:
        raise HTTPException(status_code=404, detail=f"Venta #{data.venta_id} no encontrada.")

    # 2. VALIDAR QUE HAYA ITEMS
    if not data.items:
        raise HTTPException(status_code=400, detail="Debes incluir al menos un producto para devolver.")

    # 3. VALIDAR CADA ITEM Y PREPARAR DETALLES
    try:
        detalles_objetos = []
        total_calculado = Decimal("0.0")

        for item in data.items:
            # Validar que el detalle de venta existe y pertenece a esta venta
            db_detalle = session.get(DetalleVenta, item.detalle_venta_id)
            if not db_detalle:
                raise HTTPException(
                    status_code=404,
                    detail=f"Detalle de venta #{item.detalle_venta_id} no encontrado."
                )
            if db_detalle.venta_id != data.venta_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"El detalle #{item.detalle_venta_id} no pertenece a la venta #{data.venta_id}."
                )

            # Validar que no se devuelve más de lo vendido
            if item.cantidad > db_detalle.cantidad:
                raise HTTPException(
                    status_code=400,
                    detail=f"No puedes devolver {item.cantidad} unidades — solo se vendieron {db_detalle.cantidad}."
                )

            # ✅ VALIDAR CUÁNTO YA SE DEVOLVIÓ ANTERIORMENTE DE ESTE DETALLE
            devoluciones_previas = session.exec(
                select(DetalleDevolucion).where(
                    DetalleDevolucion.detalle_venta_id == item.detalle_venta_id
                )
            ).all()
            cantidad_ya_devuelta = sum(d.cantidad for d in devoluciones_previas)
            cantidad_disponible = db_detalle.cantidad - cantidad_ya_devuelta

            if cantidad_disponible <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Este producto ya fue devuelto completamente en una devolución anterior."
                )
            if item.cantidad > cantidad_disponible:
                raise HTTPException(
                    status_code=400,
                    detail=f"Solo puedes devolver {cantidad_disponible} unidad(es) — ya se devolvieron {cantidad_ya_devuelta} anteriormente."
                )

            # Validar que el producto existe
            db_producto = session.get(Producto, item.producto_id)
            if not db_producto:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto #{item.producto_id} no encontrado."
                )

            # Revertir stock
            db_producto.stock += item.cantidad
            session.add(db_producto)

            subtotal = item.precio_unitario * item.cantidad
            total_calculado += subtotal

            detalles_objetos.append(DetalleDevolucion(
                detalle_venta_id=item.detalle_venta_id,
                producto_id=item.producto_id,
                nombre_producto=db_detalle.nombre_producto or db_producto.nombre,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario
            ))

        # 4. SI ERA VENTA A CRÉDITO — REDUCIR DEUDA DEL CLIENTE Y DE LA FACTURA
        if db_venta.es_credito:
            db_cliente = session.get(Cliente, db_venta.cliente_id)
            if db_cliente:
                # Reducir saldo global del cliente
                reduccion = min(total_calculado, db_cliente.saldo_deuda)
                db_cliente.saldo_deuda -= reduccion
                session.add(db_cliente)

            # ✅ Reducir también la deuda específica de esta factura
            reduccion_factura = min(total_calculado, db_venta.monto_en_deuda)
            db_venta.monto_en_deuda -= reduccion_factura
            session.add(db_venta)

        # 5. CREAR LA DEVOLUCIÓN
        nueva_devolucion = Devolucion(
            venta_id=data.venta_id,
            motivo=data.motivo.strip(),
            total_devolucion=total_calculado,
            fecha=datetime.now()
        )
        session.add(nueva_devolucion)
        session.flush()  # Necesitamos el ID para los detalles

        # 6. ASOCIAR DETALLES
        for detalle in detalles_objetos:
            detalle.devolucion_id = nueva_devolucion.id
            session.add(detalle)

        session.commit()
        session.refresh(nueva_devolucion)
        return nueva_devolucion

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar la devolución: {str(e)}")
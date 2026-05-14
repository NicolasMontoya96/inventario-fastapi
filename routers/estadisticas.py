from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from db.database import get_session
from decimal import Decimal
from db.schemas.estadisticasSchema import DashboardResponse
from db.models import Cliente, Producto, Usuario
from auth.auth import obtener_usuario_actual



router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)


@router.get("/", response_model=DashboardResponse)
def obtener_resumen_financiero(
    session: Session = Depends(get_session),
    # Aquí es donde ocurre la magia del bloqueo:
    usuario_actual: Usuario = Depends(obtener_usuario_actual) 
):
    """
    Este endpoint ahora es privado. 
    Solo los usuarios con un Token JWT válido pueden ver el resumen financiero.
    """
    
    # 1. CALCULAR LA CARTERA
    query_cartera = select(func.sum(Cliente.saldo_deuda))
    total_cartera = session.exec(query_cartera).first() or Decimal("0.0")

    # 2. CALCULAR EL INVENTARIO
    query_inventario = select(
        func.sum(Producto.stock * Producto.precio_compra), 
        func.sum(Producto.stock * Producto.precio_venta),  
        func.sum(Producto.stock)                           
    ).where(Producto.stock > 0) 

    resultado_inventario = session.exec(query_inventario).first()

    if resultado_inventario and resultado_inventario[0] is not None:
        valor_costo = resultado_inventario[0]
        valor_venta = resultado_inventario[1]
        total_items = resultado_inventario[2]
    else:
        valor_costo = Decimal("0.0")
        valor_venta = Decimal("0.0")
        total_items = 0

    # 3. CALCULAR LA GANANCIA PROYECTADA
    ganancia_proyectada = valor_venta - valor_costo

    # 4. ARMAR EL REPORTE
    return DashboardResponse(
        total_cartera=total_cartera,
        valor_inventario_costo=valor_costo,
        valor_inventario_venta=valor_venta,
        ganancia_proyectada=ganancia_proyectada,
        total_articulos_stock=total_items
    )
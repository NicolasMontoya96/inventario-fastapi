from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from sqlalchemy import func
from db.database import get_session
from decimal import Decimal
from db.schemas.estadisticasSchema import DashboardResponse
from db.models import Cliente, Producto



router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard"]
)


@router.get("/", response_model=DashboardResponse)
def obtener_resumen_financiero(session: Session = Depends(get_session)):
    
    # 1. CALCULAR LA CARTERA (Total de deudas de clientes)
    # select sum(saldo_deuda) from cliente;
    query_cartera = select(func.sum(Cliente.saldo_deuda))
    # .first() trae el resultado de la suma. Si es None (vacío), ponemos 0.0
    total_cartera = session.exec(query_cartera).first() or Decimal("0.0")

    # 2. CALCULAR EL INVENTARIO
    # Aquí pedimos 3 sumas diferentes en una sola consulta a la base de datos
    query_inventario = select(
        func.sum(Producto.stock * Producto.precio_compra), # Inversión total
        func.sum(Producto.stock * Producto.precio_venta),  # Venta bruta potencial
        func.sum(Producto.stock)                           # Conteo de artículos
    ).where(Producto.stock > 0) # Solo contamos lo que realmente tenemos

    # Ejecutamos la consulta. Devuelve una tupla con los 3 valores: (costo, venta, conteo)
    resultado_inventario = session.exec(query_inventario).first()

    # Extraemos los valores de la tupla (con un salvavidas de seguridad por si no hay productos)
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
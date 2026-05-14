from pydantic import BaseModel
from decimal import Decimal

class DashboardResponse(BaseModel):
    total_cartera: Decimal            # Cuánta plata le deben los clientes
    valor_inventario_costo: Decimal   # Cuánta plata hay invertida en la bodega
    valor_inventario_venta: Decimal   # Cuánto dinero sería si se vende todo
    ganancia_proyectada: Decimal      # La diferencia entre costo y venta
    total_articulos_stock: int        # Cuántos objetos físicos hay guardados
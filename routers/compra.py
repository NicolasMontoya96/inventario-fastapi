from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from db.models import Producto, Proveedor, Categoria, Cliente, Compra, DetalleCompra
from db.schemas.compraSchema import CompraCreate, DetalleCompraCreate, CompraResponse
from db.database import get_session
from sqlalchemy.exc import IntegrityError
from typing import List
from decimal import Decimal
from datetime import datetime



router = APIRouter(
    prefix="/compras",
    tags=["compras"]
)


@router.get("/", response_model=List[CompraResponse])
def obtener_historial_compras(session: Session = Depends(get_session)):
    
    statement = select(Compra).order_by(Compra.fecha.desc())
    resultados = session.exec(statement).all()
    return resultados

#------------------------------------------------------------------------------------------


@router.post("/", response_model=CompraResponse, status_code=201)
def crear_compra(compra_data: CompraCreate, session: Session = Depends(get_session)):
    
    # 1. RESOLVER EL PROVEEDOR
    db_proveedor = None

    if compra_data.proveedor_id:
        db_proveedor = session.get(Proveedor, compra_data.proveedor_id)
        if not db_proveedor:
            raise HTTPException(status_code=404, detail="El proveedor especificado no existe")
            
    elif compra_data.proveedor_nuevo:
        db_proveedor = Proveedor.model_validate(compra_data.proveedor_nuevo)
        session.add(db_proveedor)
        session.flush() 
        session.refresh(db_proveedor)

    if not db_proveedor:
        raise HTTPException(status_code=400, detail="Debe especificar un proveedor_id o los datos de un proveedor_nuevo")
    
    # 2. EMPEZAR LA LÓGICA DE LA COMPRA
    try:
        total_factura = Decimal("0.0")
        detalles_objetos = []

        # --- BUCLE DE PRODUCTOS ---
        for item in compra_data.items:
            db_producto = session.get(Producto, item.producto_id)
            
            if not db_producto:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.producto_id} no encontrado")
            
            # Usamos precio_compra
            subtotal = item.precio_compra * item.cantidad
            total_factura += subtotal
            
            # Creamos el modelo de base de datos CON EL NOMBRE CONGELADO DE RAÍZ
            nuevo_detalle = DetalleCompra(
                producto_id=db_producto.id,
                nombre_producto=db_producto.nombre,  # <--- SOLUCIÓN DE RAÍZ AQUÍ 🚀
                cantidad=item.cantidad,
                precio_compra=item.precio_compra
            )
            detalles_objetos.append(nuevo_detalle)
            
            # Sumamos el stock
            db_producto.stock += item.cantidad
            # Actualizamos el costo histórico al último costo pagado
            db_producto.precio_compra = item.precio_compra 
            
            session.add(db_producto)
        # --- FIN DEL BUCLE ---

        # 3. CREAR LA COMPRA
        nueva_compra = Compra(
            proveedor_id=db_proveedor.id,
            numero_factura=compra_data.numero_factura,
            total=total_factura, # El total exacto calculado
            fecha=datetime.now()
        )
        session.add(nueva_compra)
        session.flush() # Obtenemos el ID de la nueva_compra

        # 4. ASOCIAR DETALLES Y GUARDAR TODO
        for detalle in detalles_objetos:
            detalle.compra_id = nueva_compra.id
            session.add(detalle)

        # Confirmamos la transacción completa
        session.commit()
        session.refresh(nueva_compra)

        return nueva_compra

    # Capturamos excepciones limpiamente
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar la compra: {str(e)}")
            


from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from decimal import Decimal
from db.models import Producto, Cliente, DetalleVenta, Ventas
from db.schemas.ventaSchema import DetalleVentaCreate, VentaCreate, ClienteCreate, VentaResponse
from db.database import get_session


router = APIRouter(
    prefix="/ventas",
    tags=["ventas"]
)

#------------------------------------------------------------------------------------------------------------------

@router.post("/ventas", response_model=Ventas, status_code=201) # Cambiado a Ventas (o VentaResponse)
def crear_venta(venta_data: VentaCreate, session: Session = Depends(get_session)):
    
    # 1. RESOLVER EL CLIENTE
    db_cliente = None

    if venta_data.cliente_id:
        db_cliente = session.get(Cliente, venta_data.cliente_id)
        if not db_cliente:
            raise HTTPException(status_code=404, detail="El cliente especificado no existe")
            
    elif venta_data.cliente_nuevo:
        db_cliente = Cliente.model_validate(venta_data.cliente_nuevo)
        session.add(db_cliente)
        session.flush() 
        session.refresh(db_cliente)
        
    # Validación extra por si alguien manda el JSON sin cliente_id y sin cliente_nuevo
    if not db_cliente:
         raise HTTPException(status_code=400, detail="Debe especificar un cliente_id o los datos de un cliente_nuevo")

    # 2. EMPEZAR LA LÓGICA DE LA VENTA
    try:
        total_acumulado = Decimal("0.0")
        detalles_objetos = []

        # --- INICIO DEL BUCLE ---
        for item in venta_data.items:
            db_producto = session.get(Producto, item.producto_id)
            
            if not db_producto:
                raise HTTPException(status_code=404, detail=f"Producto con ID {item.producto_id} no encontrado")

            if db_producto.stock < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para {db_producto.nombre}. Disponible: {db_producto.stock}")

            subtotal = item.precio_unitario * item.cantidad
            total_acumulado += subtotal

            nuevo_detalle = DetalleVenta(
                producto_id=db_producto.id,
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario
            )
            detalles_objetos.append(nuevo_detalle)

            db_producto.stock -= item.cantidad
            session.add(db_producto)
        # --- FIN DEL BUCLE ---

        # 3. CÁLCULOS FINANCIEROS (¡Ahora están fuera del bucle!)
        deuda_generada = total_acumulado - venta_data.cuota_inicial

        if venta_data.es_credito:
            if deuda_generada < 0:
                raise HTTPException(
                    status_code=400,
                    detail="La cuota inicial no puede ser mayor al total en una venta a crédito"
                )
            # Sumamos la nueva deuda al saldo actual del cliente
            db_cliente.saldo_deuda += deuda_generada
            session.add(db_cliente)
            
        else:
            # 3.5 VALIDACIÓN DE PAGO (NUEVA REGLA)
            if venta_data.cuota_inicial != total_acumulado:
                raise HTTPException(
                    status_code=400,
                    detail=f"Error en el pago: Para ventas de contado, la cuota inicial ({venta_data.cuota_inicial}) debe ser igual al total ({total_acumulado})."
                )

        # 4. CREAR LA VENTA (EL ENCABEZADO)
        nueva_venta = Ventas(
            cliente_id=db_cliente.id,
            total_venta=total_acumulado,
            cuota_inicial=venta_data.cuota_inicial,
            monto_en_deuda=deuda_generada if venta_data.es_credito else Decimal("0.0"),
            es_credito=venta_data.es_credito,
            metodo_pago=venta_data.metodo_pago
        )
            
        session.add(nueva_venta)
        session.flush() 

        # 5. ASOCIAR DETALLES Y GUARDAR TODO
        for detalle in detalles_objetos:
            detalle.venta_id = nueva_venta.id
            session.add(detalle)

        # EL MOMENTO DE LA VERDAD
        session.commit()
        session.refresh(nueva_venta)
        
        return nueva_venta

    # Manejo de errores separado para no ocultar nuestras propias validaciones
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback() 
        raise HTTPException(status_code=500, detail=f"Error al procesar la venta: {str(e)}")
    
#-----------------------------------------------------------------------------------------------------
@router.get("/", response_model=list[VentaResponse])
def ventas(session: Session = Depends(get_session)):
    statement = select(Ventas).order_by(Ventas.fecha.desc()) # Ordenado por fecha, las más nuevas primero
    return session.exec(statement).all()
    

                

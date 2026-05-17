from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from db.models import Producto, Proveedor, Categoria, Compra, DetalleCompra  # MODIFICADO: Añadidas Compra y DetalleCompra
from db.schemas.productoSchema import ProductoCreate, ProductoResponse, ProductoUpdate, ProductoList, ProductoBase
from db.database import get_session
from datetime import datetime  # MODIFICADO: Añadido para estampar la hora local de la compra

router = APIRouter(
    prefix="/productos",
    tags=["Productos"]
)

@router.get("/", response_model=list[ProductoList])
def productos(session: Session = Depends(get_session)):
     return session.exec(select(Producto)).all()


#------------------------------------------------------------------------------------------------
@router.post("/", response_model=ProductoResponse, status_code=201)
def create_producto(producto: ProductoCreate, session: Session= Depends(get_session)):

    db_proveedor = session.get(Proveedor, producto.proveedor_id)
    if not db_proveedor:
       raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # 1. Validamos y guardamos el producto en la base de datos
    db_producto = Producto.model_validate(producto)
    session.add(db_producto)
    session.commit()
    session.refresh(db_producto)
    
    # 2. ¡LA MAGIA AUTOMÁTICA DE LA OPCIÓN B!
    # Si el producto nace con existencias físicas en el stock, creamos su factura de compra
    if db_producto.stock > 0:
        try:
            # Multiplicamos el stock inicial por el precio_costo real enviado desde el formulario
            total_invertido = db_producto.stock * db_producto.precio_costo
            
            # Generamos de forma automática el encabezado de la compra para el proveedor
            nueva_compra = Compra(
                proveedor_id=db_producto.proveedor_id,
                fecha=datetime.now(),
                numero_factura=f"STOCK-INICIAL-{db_producto.id}",
                total=total_invertido
            )
            session.add(nueva_compra)
            session.commit()
            session.refresh(nueva_compra)
            
            # Guardamos el desglose del artículo comprado vinculándolo a la factura anterior
            nuevo_detalle_compra = DetalleCompra(
                compra_id=nueva_compra.id,
                producto_id=db_producto.id,
                cantidad=db_producto.stock,
                precio_compra=db_producto.precio_costo
            )
            session.add(nuevo_detalle_compra)
            session.commit()
            
        except Exception as error_contable:
            # Si la factura automática falla, se limpia la transacción contable
            # pero no bloqueamos el retorno del producto creado
            session.rollback()
            print(f"Alerta del Sistema: No se pudo generar la compra automática de stock inicial: {error_contable}")
    
    return db_producto
#----------------------------------------------------------------------------------------------------

@router.patch("/{id}", response_model=ProductoResponse)
def actualizar_producto(id: int, producto_data: ProductoUpdate, session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if producto_data.proveedor_id:
        if not session.get(Proveedor, producto_data.proveedor_id):
            raise HTTPException(status_code=404, detail="Nuevo proveedor no encontrado")
            
    if producto_data.categoria_id:
        if not session.get(Categoria, producto_data.categoria_id):
            raise HTTPException(status_code=404, detail="Nueva categoría no encontrada")

    datos_nuevos = producto_data.model_dump(exclude_unset=True)
    db_producto.sqlmodel_update(datos_nuevos)
    
    session.add(db_producto)
    session.commit()
    session.refresh(db_producto)
    return db_producto

#------------------------------------------------------------------------------------------------
@router.delete("/{id}")
def eliminar_producto(id: int, session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    session.delete(db_producto)
    session.commit()
    return {"message": f"Producto '{db_producto.nombre}' eliminado correctamente"}
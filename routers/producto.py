from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from auth.auth import obtener_usuario_actual
from sqlmodel import Session, select
from db.models import Producto, Proveedor, Categoria, Compra, DetalleCompra  # MODIFICADO: Añadidas Compra y DetalleCompra
from db.schemas.productoSchema import ProductoCreate, ProductoResponse, ProductoUpdate, ProductoList, ProductoBase
from db.database import get_session
from datetime import datetime  # MODIFICADO: Añadido para estampar la hora local de la compra

import cloudinary
import cloudinary.uploader
import os

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
)

router = APIRouter(
    prefix="/productos",
    tags=["Productos"]
)

@router.get("/", response_model=list[ProductoList])
def productos(session: Session = Depends(get_session)):
    return session.exec(select(Producto).where(Producto.activo == True)).all()


@router.get("/{id}", response_model=ProductoResponse)
def obtener_producto(id: int, session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto or not db_producto.activo:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return db_producto

#------------------------------------------------------------------------------------------------
@router.post("/", response_model=ProductoResponse, status_code=201, dependencies=[Depends(obtener_usuario_actual)])
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
            total_invertido = db_producto.stock * db_producto.precio_compra

            nueva_compra = Compra(
                proveedor_id=db_producto.proveedor_id,
                fecha=datetime.now(),
                numero_factura=f"STOCK-INICIAL-{db_producto.id}",
                total=total_invertido
            )
            session.add(nueva_compra)
            session.commit()
            session.refresh(nueva_compra)

            nuevo_detalle_compra = DetalleCompra(
                compra_id=nueva_compra.id,
                producto_id=db_producto.id,
                cantidad=db_producto.stock,
                precio_compra=db_producto.precio_compra
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

@router.patch("/{id}", response_model=ProductoResponse, dependencies=[Depends(obtener_usuario_actual)])
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
@router.delete("/{id}", dependencies=[Depends(obtener_usuario_actual)])
def eliminar_producto(id: int, session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db_producto.activo = False
    
    session.add(db_producto)
    session.commit()
    
    return {"message": f"Producto '{db_producto.nombre}' ocultado del catálogo correctamente"}


#------------------------------------------------------------------------------------------------
@router.post("/{id}/imagen", response_model=ProductoResponse, dependencies=[Depends(obtener_usuario_actual)])
def subir_imagen_producto(id: int, archivo: UploadFile = File(...), session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    resultado = cloudinary.uploader.upload(
        archivo.file,
        folder="m-accesorios/productos",
        public_id=f"producto_{id}",
        overwrite=True,
        resource_type="image",
    )

    db_producto.imagen_url = resultado["secure_url"]
    session.add(db_producto)
    session.commit()
    session.refresh(db_producto)
    return db_producto

#------------------------------------------------------------------------------------------------
@router.delete("/{id}/imagen", response_model=ProductoResponse, dependencies=[Depends(obtener_usuario_actual)])
def eliminar_imagen_producto(id: int, session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    if not db_producto.imagen_url:
        raise HTTPException(status_code=400, detail="Este producto no tiene foto para eliminar")

    try:
        cloudinary.uploader.destroy(f"m-accesorios/productos/producto_{id}")
    except Exception as error_cloudinary:
        print(f"Alerta del Sistema: No se pudo eliminar la imagen {id} de Cloudinary: {error_cloudinary}")

    db_producto.imagen_url = None
    session.add(db_producto)
    session.commit()
    session.refresh(db_producto)
    return db_producto
from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from db.models import Producto, Proveedor, Categoria
from db.schemas.productoSchema import ProductoCreate, ProductoResponse, ProductoUpdate, ProductoList, ProductoBase
from db.database import get_session

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
    
    
    db_producto =  Producto.model_validate(producto)
    session.add(db_producto)
    session.commit()
    session.refresh(db_producto)
    
    return db_producto
#----------------------------------------------------------------------------------------------------

@router.patch("/{id}", response_model=ProductoResponse)
def actualizar_producto(id: int, producto_data: ProductoUpdate, session: Session = Depends(get_session)):
    db_producto = session.get(Producto, id)
    if not db_producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    # Si se intenta cambiar el proveedor o la categoría, validamos que existan
    if producto_data.proveedor_id:
        if not session.get(Proveedor, producto_data.proveedor_id):
            raise HTTPException(status_code=404, detail="Nuevo proveedor no encontrado")
            
    if producto_data.categoria_id:
        if not session.get(Categoria, producto_data.categoria_id):
            raise HTTPException(status_code=404, detail="Nueva categoría no encontrada")

    # Extraemos los datos enviados (ignorando los nulos)
    datos_nuevos = producto_data.model_dump(exclude_unset=True)
    
    # Actualizamos el objeto de la DB
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

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from db.models import Proveedor
from db.schemas.proveedorSchema import ProveedorList, ProveedorCreate, ProveedorResponse, ProveedorUpdate
from db.database import get_session


router = APIRouter(prefix="/proveedores",
                   tags=["proveedores"],
                   responses={404: {"message": "No encontrado"}})

@router.get("/", response_model=list[ProveedorResponse])
def proveedores(session: Session = Depends(get_session)):
    # Ejecutamos y retornamos de una vez
    return session.exec(select(Proveedor)).all()



@router.get("/{id}", response_model=ProveedorResponse)
def buscar_proveedor(id: int, session: Session = Depends(get_session)):
      
    db_proveedor = session.get(Proveedor, id)
    if not db_proveedor:
       raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    return db_proveedor



@router.post("/", response_model=ProveedorResponse, status_code=201)
def create_proveedor(proveedor: ProveedorCreate, session: Session = Depends(get_session)):
    db_proveedor = Proveedor.model_validate(proveedor)
    session.add(db_proveedor)
    session.commit()
    session.refresh(db_proveedor)
    return db_proveedor



@router.patch("/{id}", response_model=ProveedorResponse)
def actualizar_proveedor(id: int, proveedor_data: ProveedorUpdate, session: Session = Depends(get_session)):
    db_proveedor = session.get(Proveedor, id)
    if not db_proveedor:
       raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    # 2. Extraemos los datos nuevos como diccionario
    # exclude_unset=True evita que los campos que el usuario no envió se vuelvan None
    extra_data = proveedor_data.model_dump(exclude_unset=True)

    db_proveedor.sqlmodel_update(extra_data)
    # 4. Persistencia
    session.add(db_proveedor)
    session.commit()
    session.refresh(db_proveedor)

    return db_proveedor




@router.delete("/{id}")
def eliminar_proveedor(id: int, session: Session = Depends(get_session)):
      
    db_proveedor = session.get(Proveedor, id)
    if not db_proveedor:
       raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    
    session.delete(db_proveedor) # Solo ejecutas la acción
    session.commit() # Confirmas el borrado permanentemente
    
    return {"message": "Proveedor eliminado correctamente"}


       
       




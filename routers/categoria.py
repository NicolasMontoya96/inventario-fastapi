from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError
from db.database import get_session
from db.models import Categoria
from db.schemas.categoriaSchema import CategoriaCreate, CategoriaResponse, CategoriaUpdate

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"]
)

@router.get("/", response_model=list[CategoriaResponse])
def listar_categorias(session: Session = Depends(get_session)):
    return session.exec(select(Categoria)).all()




@router.post("/", response_model=CategoriaResponse)
def crear_categoria(categoria: CategoriaCreate, session: Session = Depends(get_session)):
    statement = select(Categoria).where(Categoria.nombre == categoria.nombre)
    existente = session.exec(statement).first()
    if existente:
        raise HTTPException(
            status_code=400, 
            detail=f"Error: La categoría '{categoria.nombre}' ya está registrada."
        )
    # --- PASO 2: INTENTO DE GUARDADO ---
    db_categoria = Categoria.model_validate(categoria)
    try:
        session.add(db_categoria)
        session.commit()
        session.refresh(db_categoria)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una categoría con el nombre '{db_categoria.nombre}'"
        )
    return db_categoria



@router.patch("/{id}", response_model=CategoriaResponse)
def actualizar_categoria(id: int, categoria_data: CategoriaUpdate, session: Session = Depends(get_session)):
    db_categoria = session.get(Categoria, id)
    if not db_categoria:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    
    extra_data = categoria_data.model_dump(exclude_unset=True)
    db_categoria.sqlmodel_update(extra_data)

    try:
        session.add(db_categoria)
        session.commit()
        session.refresh(db_categoria)

    except IntegrityError:
        # Si entra aquí, es porque el nombre nuevo ya existe en otra categoría
        session.rollback() # ¡IMPORTANTE! Limpia la transacción fallida
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe una categoría con el nombre '{categoria_data.nombre}'"
        )

    return db_categoria


@router.delete("/{id}")
def eliminar_categoria(id: int, session: Session = Depends(get_session)):
    db_categoria = session.get(Categoria, id)

    if not db_categoria:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    try:
        session.delete(db_categoria)
        session.commit()
        return {"message": "Categoría eliminada correctamente"}
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: Esta categoría tiene productos asociados."
        )



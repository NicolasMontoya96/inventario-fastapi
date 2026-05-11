from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from db.database import get_session
from db.models import Categoria
from db.schemas.categoriaSchema import CategoriaCreate, CategoriaResponse

router = APIRouter(
    prefix="/categorias",
    tags=["Categorías"]
)

@router.get("/", response_model=list[CategoriaResponse])
def listar_categorias(session: Session = Depends(get_session)):
    return session.exec(select(Categoria)).all()

@router.post("/", response_model=CategoriaResponse)
def crear_categoria(categoria: CategoriaCreate, session: Session = Depends(get_session)):
    db_categoria = Categoria.model_validate(categoria)
    session.add(db_categoria)
    session.commit()
    session.refresh(db_categoria)
    return db_categoria






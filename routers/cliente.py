from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from db.models import Producto, Proveedor, Categoria, Cliente
from db.schemas.clienteSchema import ClienteCreate, ClienteResponse, ClienteUpdate, ClienteBase
from db.database import get_session
from sqlalchemy.exc import IntegrityError
from typing import List

router = APIRouter(
    prefix="/clientes",
    tags=["clientes"]
)


@router.get("/", response_model=List[ClienteResponse])
def clientes(session: Session = Depends(get_session)):
    statement = select(Cliente).order_by(Cliente.nombre)
    clientes = session.exec(statement).all()
    return clientes


@router.post("/clientes", response_model=ClienteResponse, status_code=201)
def crear_cliente(cliente: ClienteCreate, session: Session= Depends(get_session)):
    statement = select(Cliente).where(Cliente.email == cliente.email)
    email_existente = session.exec(statement).first()

    if email_existente:
        raise HTTPException(
            status_code=400,
            detail=f"Error: El email '{cliente.email}' ya está registrado."
        )
    
    db_cliente = Cliente.model_validate(cliente)
    try:
        session.add(db_cliente)
        session.commit()
        session.refresh(db_cliente)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error de integridad: No se pudo registrar al cliente '{db_cliente.nombre}'"
        )

    return db_cliente


@router.patch("/{id}", response_model=ClienteResponse)
def actualizar_cliente(id: int, cliente_data: ClienteUpdate, session: Session = Depends(get_session)):
    db_cliente = session.get(Cliente, id)
    
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    datos_nuevos = cliente_data.model_dump(exclude_unset=True)
    db_cliente.sqlmodel_update(datos_nuevos)
    session.add(db_cliente)

    try:
        session.commit()
        session.refresh(db_cliente)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="El email ya existe en otro cliente")
    
    return db_cliente



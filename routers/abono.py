from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from decimal import Decimal
from db.models import Cliente, Abono
from db.schemas.abonoSchema import  AbonoResponse, AbonoCreate
from db.database import get_session


router = APIRouter(
    prefix="/abonos",
    tags=["Abonos"]
)

@router.post("/", response_model=AbonoResponse, status_code=201)
def registrar_abono(abono_data: AbonoCreate, session: Session = Depends(get_session)):

    db_cliente = session.get(Cliente, abono_data.cliente_id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    if db_cliente.saldo_deuda <=0:
        raise HTTPException(status_code=400, detail="Este cliente no tiene deudas pendientes.")
    
    # 3. Validar que el abono no sea mayor a la deuda (Caja Cuadrada)
    if abono_data.monto_abonado > db_cliente.saldo_deuda:
        raise HTTPException(
            status_code=400, 
            detail=f"El abono ({abono_data.monto_abonado}) supera la deuda actual ({db_cliente.saldo_deuda})."
        )
    
    try:
        # 4. Actualizar la cartera: Restamos el dinero a la deuda del cliente
        db_cliente.saldo_deuda -= abono_data.monto_abonado
        session.add(db_cliente)

        # 5. Crear el registro histórico del abono
        nuevo_abono = Abono.model_validate(abono_data)
        session.add(nuevo_abono)

        # 6. Guardar todo en la base de datos de forma atómica
        session.commit()
        session.refresh(nuevo_abono)

        return nuevo_abono

    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Error al procesar el abono: {str(e)}")
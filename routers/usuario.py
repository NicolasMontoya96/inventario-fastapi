from fastapi import APIRouter, Depends, HTTPException, status
from db.database import get_session
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import timedelta
from db.models import Usuario
from db.schemas.userSchema import UsuarioCreate, Token, UsuarioResponse
from auth.auth import obtener_password_hash, verificar_password, crear_token_acceso, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/autenticacion",
    tags=["autenticacion"]
)
# ---------------------------------------------------------
# 1. EL ENDPOINT PARA REGISTRAR AL USUARIO (Tu papá, tú, etc.)
# ---------------------------------------------------------
@router.post("/registro", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def registrar_usuario(usuario: UsuarioCreate, session: Session = Depends(get_session)):
    
    # Verificamos que el nombre de usuario no exista ya
    usuario_db = session.exec(select(Usuario).where(Usuario.username == usuario.username)).first()
    if usuario_db:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
    
    # ¡LA MAGIA AQUÍ! Encriptamos la contraseña plana antes de guardarla
    password_encriptada = obtener_password_hash(usuario.password)
    
    # Creamos el usuario con el hash, NUNCA con la contraseña real
    nuevo_usuario = Usuario(
        username=usuario.username,
        password_hash=password_encriptada,
        rol=usuario.rol 
    )
    
    session.add(nuevo_usuario)
    session.commit()
    session.refresh(nuevo_usuario)
    return nuevo_usuario


# ---------------------------------------------------------
# 2. EL ENDPOINT DE LOGIN (La taquilla para pedir el Token)
# ---------------------------------------------------------
@router.post("/login", response_model=Token)
def login_para_obtener_token(
    # OAuth2PasswordRequestForm es especial: lee los datos como formulario, no como JSON
    form_data: OAuth2PasswordRequestForm = Depends(), 
    session: Session = Depends(get_session)
):
    # 1. Buscamos al usuario en la base de datos
    usuario = session.exec(select(Usuario).where(Usuario.username == form_data.username)).first()
    
    # 2. Si no existe o la contraseña no coincide, lanzamos error genérico (por seguridad)
    if not usuario or not verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # 3. Si todo está perfecto, "imprimimos" el Token (el gafete)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token_generado = crear_token_acceso(
        data={"sub": usuario.username, "rol": usuario.rol},
        expires_delta=access_token_expires
    )
    
    # 4. El estándar exige devolver exactamente este JSON
    return {"access_token": token_generado, "token_type": "bearer"}
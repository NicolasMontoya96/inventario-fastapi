from datetime import datetime, timedelta, timezone
import os
import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from db import database 
from db.models import Usuario 
from db.database import get_session


password_hash = PasswordHash((BcryptHasher(),))


SECRET_KEY = os.getenv("SECRET_KEY", "clave_de_respaldo")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="autenticacion/login")

# --- FUNCIONES DE SEGURIDAD ---

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Comprueba si la contraseña plana coincide con el hash guardado"""
    return password_hash.verify(plain_password, hashed_password)

def obtener_password_hash(password: str) -> str:
    """Convierte una contraseña plana en un hash indescifrable"""
    return password_hash.hash(password)

def crear_token_acceso(data: dict, expires_delta: timedelta | None = None):
    """Fábrica de carnets (Tokens JWT)"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Agregamos la fecha de expiración al token
    to_encode.update({"exp": expire})
    
    # Firmamos el token con tu clave secreta
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- EL CONTROL DE ACCESO (DEPENDENCIA) ---

def obtener_usuario_actual(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    """
    Esta es la función que pondremos de "escudo" en las rutas.
    Toma el token, lo lee, y si es válido, busca al usuario en la BD.
    """
    credenciales_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 1. Intentamos leer el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credenciales_exception
    except jwt.InvalidTokenError:
        # Si el token expiró o fue manipulado
        raise credenciales_exception
    
    # 2. Buscamos que el usuario siga existiendo en la base de datos
    usuario = session.exec(select(Usuario).where(Usuario.username == username)).first()
    if usuario is None:
        raise credenciales_exception
        
    return usuario
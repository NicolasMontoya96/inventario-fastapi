from sqlmodel import SQLModel
from typing import Optional

# 1. Este se usa para RECIBIR los datos (POST /usuarios)
class UsuarioCreate(SQLModel):
    username: str
    password: str
    rol: Optional[str] = "admin"

# 2. Este se usa para DEVOLVER los datos (lo que ve el cliente)
class UsuarioResponse(SQLModel):
    id: int
    username: str
    rol: str
    is_active: bool


class Token(SQLModel):
    access_token: str
    token_type: str
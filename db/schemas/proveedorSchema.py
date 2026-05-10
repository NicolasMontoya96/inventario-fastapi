from sqlmodel import SQLModel, Field
from typing import Optional

# 1. BASE: Lo que es común a todos (Evita repetir código)
class ProveedorBase(SQLModel):
    nombre_empresa: str = Field(min_length=3, max_length=100)
    nit: Optional[str] = Field(index=True, unique=True)
    contacto: Optional[str] = None
    descripcion: Optional[str] = None

# 2. CREATE: Lo que pides en el formulario de registro
# Hereda de Base, por lo tanto requiere nombre, nit, etc.
class ProveedorCreate(ProveedorBase):
    pass  # No necesita nada extra, usa exactamente lo de la Base

# 3. LIST: Lo que se ve en la tabla principal (Ligero)
class ProveedorList(SQLModel):
    id: int
    nombre_empresa: str
    nit: str
    # Aquí no enviamos contacto ni descripción para que la lista sea rápida

# 4. RESPONSE/DETAIL: Lo que se ve al presionar "Ver Proveedor" (Completo)
class ProveedorResponse(ProveedorBase):
    id: int

# 5. UPDATE: Lo que usas para editar (Todo opcional)
class ProveedorUpdate(SQLModel):
    nombre_empresa: Optional[str] = None
    nit: Optional[str] = None
    contacto: Optional[str] = None
    descripcion: Optional[str] = None
from fastapi import FastAPI, Depends # <-- Asegúrate de importar Depends
from fastapi.middleware.cors import CORSMiddleware
from db.database import create_db_and_tables
from routers import proveedor, producto, categoria, cliente, venta, compra, estadisticas, usuario

# Importamos tu función de seguridad (ajusta la ruta si tu archivo se llama diferente)
from auth.auth import obtener_usuario_actual 

app = FastAPI(title="API de Inventario")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# -------------------------------------------------------------------------------
# EL CANDADO MAESTRO: Exige un Token válido para dejar pasar la petición
candado = [Depends(obtener_usuario_actual)]

# Aplicamos el candado a todas las rutas que manejan información del negocio
app.include_router(proveedor.router, dependencies=candado)
app.include_router(producto.router, dependencies=candado)
app.include_router(categoria.router, dependencies=candado)
app.include_router(cliente.router, dependencies=candado)
app.include_router(compra.router, dependencies=candado)
app.include_router(venta.router, dependencies=candado)
app.include_router(estadisticas.router, dependencies=candado)

# ¡RUTAS PÚBLICAS! (Sin candado)
# La ruta de usuarios DEBE ser pública para que procese el Login y devuelva el Token.
app.include_router(usuario.router)
# -------------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
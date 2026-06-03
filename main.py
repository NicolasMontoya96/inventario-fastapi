from fastapi import FastAPI, Depends 
from fastapi.middleware.cors import CORSMiddleware
from db.database import create_db_and_tables
from routers import proveedor, producto, categoria, cliente, venta, compra, estadisticas, usuario, devolucion


from auth.auth import obtener_usuario_actual 

app = FastAPI(title="API de Inventario")


origenes_permitidos = [
    "http://localhost:5173",                     
    "http://127.0.0.1:5173",                     
    "https://jazzy-entremet-597d36.netlify.app" 
]

# 2. Aplicamos la lista al CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


candado = [Depends(obtener_usuario_actual)]


app.include_router(proveedor.router, dependencies=candado)
app.include_router(producto.router, dependencies=candado)
app.include_router(categoria.router, dependencies=candado)
app.include_router(cliente.router, dependencies=candado)
app.include_router(compra.router, dependencies=candado)
app.include_router(venta.router, dependencies=candado)
app.include_router(estadisticas.router, dependencies=candado)
app.include_router(devolucion.router, dependencies=candado)


app.include_router(usuario.router)
# -------------------------------------------------------------------------------

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
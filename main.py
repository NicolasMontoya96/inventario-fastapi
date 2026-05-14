from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from db.database import create_db_and_tables
from routers import proveedor, producto, categoria, cliente, venta, compra, estadisticas, usuario
from db import models



app = FastAPI(title="API de Inventario")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)
#-------------------------------------------------------------------------------


app.include_router(proveedor.router)
app.include_router(producto.router)
app.include_router(categoria.router)
app.include_router(cliente.router)
app.include_router(compra.router)
app.include_router(venta.router)
app.include_router(estadisticas.router)
app.include_router(usuario.router)


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
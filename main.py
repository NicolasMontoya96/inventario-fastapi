from fastapi import FastAPI
from db.database import create_db_and_tables
from routers import proveedor, producto, categoria


app = FastAPI()

app.include_router(proveedor.router)
app.include_router(producto.router)
app.include_router(categoria.router)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
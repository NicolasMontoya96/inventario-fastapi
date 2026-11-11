from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from db.database import create_db_and_tables, engine
from routers import proveedor, producto, categoria, cliente, venta, compra, estadisticas, usuario, devolucion, pedidoWeb
from routers.pedidoWeb import liberar_pedidos_vencidos
from auth.auth import obtener_usuario_actual
from limiter import limiter


scheduler = BackgroundScheduler()


def tarea_liberar_pedidos_vencidos():
    with Session(engine) as session:
        liberar_pedidos_vencidos(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    scheduler.add_job(tarea_liberar_pedidos_vencidos, "interval", minutes=2)
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="API de Inventario", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


origenes_permitidos = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://jazzy-entremet-597d36.netlify.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origenes_permitidos,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


candado = [Depends(obtener_usuario_actual)]


app.include_router(proveedor.router, dependencies=candado)
app.include_router(producto.router)
app.include_router(categoria.router)
app.include_router(cliente.router, dependencies=candado)
app.include_router(compra.router, dependencies=candado)
app.include_router(venta.router, dependencies=candado)
app.include_router(estadisticas.router, dependencies=candado)
app.include_router(devolucion.router, dependencies=candado)
app.include_router(pedidoWeb.router)  # sin dependencies=candado — es público

app.include_router(usuario.router)
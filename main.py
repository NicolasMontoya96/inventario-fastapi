import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from alembic import command
from alembic.config import Config

from db.database import create_db_and_tables, engine
from routers import proveedor, producto, categoria, cliente, venta, compra, estadisticas, usuario, devolucion, pedidoWeb
from routers.pedidoWeb import liberar_pedidos_vencidos
from auth.auth import obtener_usuario_actual
from limiter import limiter


scheduler = BackgroundScheduler()


def tarea_liberar_pedidos_vencidos():
    with Session(engine) as session:
        liberar_pedidos_vencidos(session)


def aplicar_migraciones():
    """Corre `alembic upgrade head` automáticamente al arrancar.

    No hay Procfile/comando de release en este repo que lo haga por fuera,
    así que lo disparamos aquí para que un deploy en Railway nunca se quede
    con columnas o tablas nuevas sin crear (p. ej. producto.imagen_url, que
    create_all() no agrega porque nunca altera tablas existentes).

    Importante: se llama DESPUÉS de create_db_and_tables() (ver lifespan).
    En una base totalmente nueva (primer deploy), create_all() crea todas
    las tablas de una sola vez respetando las FKs; si Alembic corriera
    primero, su migración trataría de crear detallepedidoweb con una FK
    hacia producto antes de que producto exista, y fallaría con
    'relation "producto" does not exist'. Corriendo después, la migración
    simplemente ve que todo ya existe y no hace nada; en una base de
    producción que YA tenía producto/categoria/etc. pero no pedidoweb ni
    imagen_url, create_all() tampoco altera la tabla producto existente,
    así que la migración sigue siendo la única que agrega esa columna.
    """
    raiz_proyecto = Path(__file__).resolve().parent
    alembic_cfg = Config(str(raiz_proyecto / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(raiz_proyecto / "alembic"))
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as error_migracion:
        # No tumbamos el arranque de la API por esto, pero sí lo dejamos
        # bien visible en los logs de Railway para no pasarlo por alto.
        print(f"ALERTA: no se pudieron aplicar las migraciones de Alembic: {error_migracion}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    aplicar_migraciones()
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
    # Puerto al que Vite cae automáticamente cuando el 5173 ya está ocupado
    # (por ejemplo, con la tienda-m-accesorios corriendo en paralelo en local).
    "http://localhost:5174",
    "http://127.0.0.1:5174",
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
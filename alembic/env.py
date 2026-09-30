# alembic/env.py
from __future__ import annotations
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys
from pathlib import Path



# --- RUTA PROYECTO Y .ENV ---
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT_DIR / ".env")
except Exception:
    pass

# --- CONFIG BASE ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- IMPORTA Base Y MODELOS ---
from db_connection import Base           # usa la MISMA Base del proyecto
import orm                               # importa tus modelos para poblar metadata

target_metadata = Base.metadata          # <- ESTO es lo que necesita Alembic

# --- URL SÍNCRONA PARA ALEMBIC ---
# Toma DATABASE_URL (async) y fuerzala a psycopg (sync)
db_url = os.getenv("DATABASE_URL")  # e.g. postgresql+asyncpg://user:pass@127.0.0.1:5432/db
if db_url:
    sync_url = db_url.replace("+asyncpg", "+psycopg")
    config.set_main_option("sqlalchemy.url", sync_url)   # <--- CLAVE y VALOR

def run_migrations_offline() -> None:
    """Ejecuta migraciones en modo 'offline'."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Ejecuta migraciones en modo 'online'."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

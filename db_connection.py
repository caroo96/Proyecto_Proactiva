# db_connection.py
import os
import ssl
from typing import AsyncGenerator
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

# Cargar .env desde la raíz
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
ENV = os.getenv("ENV", "development")  # 👈 clave

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definida. Revisa tu .env")

# 🔥 Configuración SSL correcta para asyncpg
connect_args = {}

if ENV == "production":
    ssl_context = ssl.create_default_context()
    connect_args = {"ssl": ssl_context}

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
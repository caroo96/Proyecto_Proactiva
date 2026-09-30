# routers/programas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from db_connection import get_session
from orm import Programa, Usuario
from schemas import ProgramaIn, ProgramaOut
from auth import get_current_user, require_role

router = APIRouter(
    prefix="/programas",
    tags=["Programas"]
)


@router.post("/", response_model=ProgramaOut, status_code=status.HTTP_201_CREATED)
async def create_programa(
    payload: ProgramaIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("coordinador"))
):
    """Crear programa (solo coordinadores)"""
    # Verificar si ya existe
    result = await session.execute(
        select(Programa).where(Programa.codigo == payload.codigo)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un programa con ese código"
        )
    
    programa = Programa(**payload.model_dump())
    session.add(programa)
    await session.commit()
    await session.refresh(programa)
    
    return programa


@router.get("/", response_model=List[ProgramaOut])
async def list_programas(
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Listar todos los programas"""
    result = await session.execute(select(Programa))
    return result.scalars().all()


@router.get("/{programa_id}", response_model=ProgramaOut)
async def get_programa(
    programa_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener programa por ID"""
    result = await session.execute(
        select(Programa).where(Programa.id == programa_id)
    )
    programa = result.scalar_one_or_none()
    
    if not programa:
        raise HTTPException(status_code=404, detail="Programa no encontrado")
    
    return programa
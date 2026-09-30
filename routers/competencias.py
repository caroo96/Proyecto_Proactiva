# routers/competencias.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from db_connection import get_session
from orm import Competencia, Usuario
from schemas import CompetenciaIn, CompetenciaOut
from auth import get_current_user, require_role

router = APIRouter(
    prefix="/competencias",
    tags=["Competencias"]
)


@router.post("/", response_model=CompetenciaOut, status_code=status.HTTP_201_CREATED)
async def create_competencia(
    payload: CompetenciaIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("coordinador"))
):
    """Crear competencia (solo coordinadores)"""
    # Verificar si ya existe
    result = await session.execute(
        select(Competencia).where(Competencia.nombre == payload.nombre)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una competencia con ese nombre"
        )
    
    competencia = Competencia(**payload.model_dump())
    session.add(competencia)
    await session.commit()
    await session.refresh(competencia)
    
    return competencia


@router.get("/", response_model=List[CompetenciaOut])
async def list_competencias(
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Listar todas las competencias"""
    result = await session.execute(select(Competencia))
    return result.scalars().all()


@router.get("/{competencia_id}", response_model=CompetenciaOut)
async def get_competencia(
    competencia_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener competencia por ID"""
    result = await session.execute(
        select(Competencia).where(Competencia.id == competencia_id)
    )
    competencia = result.scalar_one_or_none()
    
    if not competencia:
        raise HTTPException(status_code=404, detail="Competencia no encontrada")
    
    return competencia
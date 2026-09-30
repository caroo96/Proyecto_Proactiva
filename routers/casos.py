# routers/casos.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from db_connection import get_session
from orm import Caso, Competencia, Programa, Usuario
from schemas import CasoIn, CasoOut, CasoDetalle
from auth import get_current_user, require_role

router = APIRouter(
    prefix="/casos",
    tags=["Casos"]
)


@router.post("/", response_model=CasoOut, status_code=status.HTTP_201_CREATED)
async def create_caso(
    payload: CasoIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """Crear nuevo caso (solo profesores y coordinadores)"""
    try:
        print("current_user",current_user)
        caso = Caso(
            titulo=payload.titulo,
            descripcion=payload.descripcion,
            creador_id=current_user.id
        )
        
        if payload.competencias_ids:
            result = await session.execute(
                select(Competencia).where(Competencia.id.in_(payload.competencias_ids))
            )
            competencias = list(result.scalars().all())
            
            if len(competencias) != len(payload.competencias_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Una o más competencias no existen"
                )
            
            caso.competencias = competencias
        
        if payload.programas_ids:
            result = await session.execute(
                select(Programa).where(Programa.id.in_(payload.programas_ids))
            )
            programas = list(result.scalars().all())
            
            if len(programas) != len(payload.programas_ids):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uno o más programas no existen"
                )
            
            caso.programas = programas
        
        session.add(caso)
        await session.commit()
        await session.refresh(caso)
        
        return caso
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ Error al crear caso: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear caso: {str(e)}"
        )



@router.get("/", response_model=List[CasoOut])
async def list_casos(
    session: AsyncSession = Depends(get_session),
    #la linea de abajo controla el token
    current_user: Usuario = Depends(get_current_user)
):
    """Listar todos los casos"""
    result = await session.execute(select(Caso))
    casos = result.scalars().all()
    return casos


@router.get("/{caso_id}", response_model=CasoDetalle)
async def get_caso(
    caso_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener caso por ID con sus relaciones"""
    result = await session.execute(
        select(Caso)
        .options(selectinload(Caso.competencias), selectinload(Caso.programas))
        .where(Caso.id == caso_id)
    )
    caso = result.scalar_one_or_none()
    
    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    return caso


@router.put("/{caso_id}", response_model=CasoOut)
async def update_caso(
    caso_id: int,
    payload: CasoIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """Actualizar caso (solo el creador o coordinadores)"""
    try:
        # Buscar caso con relaciones
        result = await session.execute(
            select(Caso)
            .options(selectinload(Caso.competencias), selectinload(Caso.programas))
            .where(Caso.id == caso_id)
        )
        caso = result.scalar_one_or_none()
        
        if not caso:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Caso no encontrado"
            )
        
        # Verificar permisos
        if caso.creador_id != current_user.id and current_user.rol != "coordinador":
        # if caso.creador_id != current_user.id and current_user.rol != "profesor":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para editar este caso"
            )
        
        # Actualizar campos
        caso.titulo = payload.titulo
        caso.descripcion = payload.descripcion
        
        # Actualizar competencias
        caso.competencias.clear()
        if payload.competencias_ids:
            result = await session.execute(
                select(Competencia).where(Competencia.id.in_(payload.competencias_ids))
            )
            competencias = result.scalars().all()
            for comp in competencias:
                caso.competencias.append(comp)
        
        # Actualizar programas
        caso.programas.clear()
        if payload.programas_ids:
            result = await session.execute(
                select(Programa).where(Programa.id.in_(payload.programas_ids))
            )
            programas = result.scalars().all()
            for prog in programas:
                caso.programas.append(prog)
        
        await session.commit()
        await session.refresh(caso)
        
        return caso
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        print(f"❌ Error al actualizar caso: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar caso: {str(e)}"
        )


@router.delete("/{caso_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_caso(
    caso_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("coordinador"))
):
    """Eliminar caso (solo coordinadores)"""
    result = await session.execute(
        select(Caso).where(Caso.id == caso_id)
    )
    caso = result.scalar_one_or_none()
    
    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    await session.delete(caso)
    await session.commit()
    
    return None
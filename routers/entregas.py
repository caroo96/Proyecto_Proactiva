# routers/entregas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from db_connection import get_session
from orm import Entrega,Caso, Usuario
from schemas import EntregaIn, EntregaOut, EntregaDetalle, EntregaUpdate
from auth import get_current_user, require_role

router = APIRouter(
    prefix="/entregas",
    tags=["Entregas"]
)


@router.post("/", response_model=EntregaOut, status_code=status.HTTP_201_CREATED)
async def create_entrega(
    payload: EntregaIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("estudiante", "profesor", "coordinador"))
):
    """
    Crear nueva entrega para un caso.
    
    Solo estudiantes pueden crear entregas para sí mismos.
    Profesores y coordinadores pueden crear entregas para demostración.
    """
    # Verificar que el caso existe
    result = await session.execute(
        select(Caso).where(Caso.id == payload.caso_id)
    )
    caso = result.scalar_one_or_none()
    
    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    entrega = Entrega(
        caso_id=payload.caso_id,
        estudiante_id=current_user.id,
        respuesta=payload.respuesta,
        retroalimentacion_estudiante=payload.retroalimentacion_estudiante,
        estado="pendiente"
    )
    
    session.add(entrega)
    await session.commit()
    await session.refresh(entrega)
    
    return entrega


@router.get("/", response_model=List[EntregaOut])
async def list_entregas(
    caso_id: int = None,
    estado: str = None,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar entregas.
    
    - Estudiantes: Solo ven sus propias entregas
    - Profesores y Coordinadores: Ven todas las entregas
    
    Filtros opcionales:
    - caso_id: Entregas de un caso específico
    - estado: pendiente, en_revision, evaluada, rechazada
    """
    query = select(Entrega)
    
    # Filtro por rol
    if current_user.rol == "estudiante":
        query = query.where(Entrega.estudiante_id == current_user.id)
    
    # Filtro por caso
    if caso_id:
        query = query.where(Entrega.caso_id == caso_id)
    
    # Filtro por estado
    if estado:
        query = query.where(Entrega.estado == estado)
    
    # Ordenar por fecha más reciente
    query = query.order_by(Entrega.fecha_entrega.desc())
    
    result = await session.execute(query)
    entregas = result.scalars().all()
    
    return entregas


@router.get("/MisEntregas", response_model=List[EntregaOut])
async def get_mis_entregas(
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener todas las entregas del usuario actual para un caso específico.
    
    Útil para ver el historial de intentos del estudiante.
    """
    result = await session.execute(
        select(Entrega)
        .where(Entrega.estudiante_id == current_user.id)
        .order_by(Entrega.fecha_entrega.desc())
    )
    entregas = result.scalars().all()
    
    return entregas


@router.get("/{entrega_id}", response_model=EntregaOut)
async def get_entrega(
    entrega_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener una entrega por ID.
    
    - Estudiantes: Solo pueden ver sus propias entregas
    - Profesores y Coordinadores: Pueden ver cualquier entrega
    """
    result = await session.execute(
        select(Entrega).where(Entrega.id == entrega_id)
    )
    entrega = result.scalar_one_or_none()
    
    if not entrega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega no encontrada"
        )
    
    # Verificar permisos
    if current_user.rol == "estudiante" and entrega.estudiante_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver esta entrega"
        )
    
    return entrega


@router.put("/{entrega_id}", response_model=EntregaOut)
async def update_entrega(
    entrega_id: int,
    payload: EntregaUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Actualizar una entrega.
    
    - Solo el estudiante creador puede actualizar su entrega
    - Solo si el estado es "pendiente" (no evaluada aún)
    """
    result = await session.execute(
        select(Entrega).where(Entrega.id == entrega_id)
    )
    entrega = result.scalar_one_or_none()
    
    if not entrega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega no encontrada"
        )
    
    # Verificar permisos
    if entrega.estudiante_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes actualizar tus propias entregas"
        )
    
    # Verificar estado
    if entrega.estado != "pendiente":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede modificar una entrega con estado '{entrega.estado}'"
        )
    
    # Actualizar campos
    if payload.titulo is not None:
        entrega.titulo = payload.titulo
    if payload.url_archivo is not None:
        entrega.url_archivo = payload.url_archivo
    if payload.tiempo_dedicado is not None:
        entrega.tiempo_dedicado = payload.tiempo_dedicado
    if payload.retroalimentacion_estudiante is not None:
        entrega.retroalimentacion_estudiante = payload.retroalimentacion_estudiante
    
    # Incrementar versión
    entrega.version += 1
    
    await session.commit()
    await session.refresh(entrega)
    
    return entrega


@router.delete("/{entrega_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entrega(
    entrega_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("coordinador"))
):
    """
    Eliminar una entrega (solo coordinadores).
    
    Esto eliminará también la evaluación asociada si existe.
    """
    result = await session.execute(
        select(Entrega).where(Entrega.id == entrega_id)
    )
    entrega = result.scalar_one_or_none()
    
    if not entrega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega no encontrada"
        )
    
    await session.delete(entrega)
    await session.commit()
    
    return None


@router.get("/caso/{caso_id}/mis-entregas", response_model=List[EntregaOut])
async def get_mis_entregas_caso(
    caso_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener todas las entregas del usuario actual para un caso específico.
    
    Útil para ver el historial de intentos del estudiante.
    """
    result = await session.execute(
        select(Entrega)
        .where(Entrega.caso_id == caso_id)
        .where(Entrega.estudiante_id == current_user.id)
        .order_by(Entrega.fecha_entrega.desc())
    )
    entregas = result.scalars().all()
    
    return entregas


@router.get("/caso/{caso_id}", response_model=list[EntregaOut])
async def get_entrega(
    caso_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener una entrega por caso_id.

    """
    result = await session.execute(
        select(Entrega)
        .where(Entrega.caso_id == caso_id)
    )
    entrega = result.scalars().all()
    
    
    return entrega
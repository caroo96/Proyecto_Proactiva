# routers/rubricas.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List

from db_connection import get_session
from orm import Rubrica, CriterioRubrica, Caso, Usuario
from schemas import RubricaIn, RubricaOut, RubricaDetalle
from auth import get_current_user, require_role

router = APIRouter(
    prefix="/rubricas",
    tags=["📋 Rúbricas"]
)


@router.post("/caso/{caso_id}", response_model=RubricaDetalle, status_code=status.HTTP_201_CREATED)
async def create_rubrica(
    caso_id: int,
    payload: RubricaIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """
    Crear rúbrica para un caso (solo el creador del caso o coordinadores)
    
    La rúbrica define los criterios de evaluación que la IA usará para evaluar entregas.
    """
    # Verificar que el caso existe
    result = await session.execute(
        select(Caso).where(Caso.id == caso_id)
    )
    caso = result.scalar_one_or_none()
    
    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )
    
    # Verificar permisos
    if caso.creador_id != current_user.id and current_user.rol != "coordinador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el creador del caso o coordinadores pueden crear rúbricas"
        )
    
    # Verificar que no exista ya una rúbrica para este caso
    result = await session.execute(
        select(Rubrica).where(Rubrica.caso_id == caso_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este caso ya tiene una rúbrica. Use PUT para actualizarla."
        )
    
    # Validar que la suma de puntajes no exceda la escala máxima
    suma_criterios = sum(c.puntaje_maximo for c in payload.criterios)
    if suma_criterios > payload.escala_maxima:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La suma de los criterios ({suma_criterios}) excede la escala máxima ({payload.escala_maxima})"
        )
    
    # Crear rúbrica
    rubrica = Rubrica(
        caso_id=caso_id,
        docente_id=current_user.id,
        nombre=payload.nombre,
        descripcion=payload.descripcion,
        tipo_rubrica=payload.tipo_rubrica,
        escala_maxima=payload.escala_maxima,
        publica=payload.publica,
        permitir_autoevaluacion=payload.permitir_autoevaluacion,
        vigente=payload.vigente
    )
    
    # Crear criterios
    for idx, criterio_data in enumerate(payload.criterios):
        criterio = CriterioRubrica(
            nombre=criterio_data.nombre,
            descripcion=criterio_data.descripcion,
            puntaje_maximo=criterio_data.puntaje_maximo,
            orden=criterio_data.orden if criterio_data.orden else idx
        )
        rubrica.criterios.append(criterio)
    
    session.add(rubrica)
    await session.commit()
    
    # Recargar con relaciones
    result = await session.execute(
        select(Rubrica)
        .options(selectinload(Rubrica.criterios))
        .where(Rubrica.id == rubrica.id)
    )
    rubrica = result.scalar_one()
    
    return rubrica


@router.get("/caso/{caso_id}", response_model=RubricaDetalle)
async def get_rubrica_by_caso(
    caso_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener la rúbrica de un caso con todos sus criterios.
    
    **Uso para IA:** Este endpoint retorna la estructura completa de evaluación
    que la IA debe usar para calificar entregas.
    """
    result = await session.execute(
        select(Rubrica)
        .options(selectinload(Rubrica.criterios))
        .where(Rubrica.caso_id == caso_id)
    )
    rubrica = result.scalar_one_or_none()
    
    if not rubrica:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este caso no tiene rúbrica definida"
        )
    
    return rubrica


@router.get("/{caso_id}", response_model=RubricaDetalle)
# @router.get("/{rubrica_id}", response_model=RubricaDetalle)
async def get_rubrica(
    caso_id: int,
    # rubrica_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """Obtener rúbrica por ID con sus criterios"""
    result = await session.execute(
        select(Rubrica)
        .options(selectinload(Rubrica.criterios))
        .where(Caso.id == caso_id)
        # .where(Rubrica.id == rubrica_id)
    )
    rubrica = result.scalar_one_or_none()
    
    if not rubrica:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rúbrica no encontrada"
        )
    
    return rubrica


@router.get("/", response_model=List[RubricaOut])
async def list_rubricas(
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """Listar todas las rúbricas (solo profesores y coordinadores)"""
    result = await session.execute(select(Rubrica))
    rubricas = result.scalars().all()
    return rubricas


@router.put("/caso/{caso_id}", response_model=RubricaDetalle)
async def update_rubrica(
    caso_id: int,
    payload: RubricaIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """
    Actualizar rúbrica para un caso (solo el creador del caso o coordinadores)
    """

    # Verificar que el caso existe
    result = await session.execute(
        select(Caso).where(Caso.id == caso_id)
    )
    caso = result.scalar_one_or_none()

    if not caso:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Caso no encontrado"
        )

    # Verificar permisos
    if caso.creador_id != current_user.id and current_user.rol != "coordinador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el creador del caso o coordinadores pueden modificar rúbricas"
        )

    # Buscar rúbrica existente
    result = await session.execute(
        select(Rubrica)
        .options(selectinload(Rubrica.criterios))
        .where(Rubrica.caso_id == caso_id)
    )
    rubrica = result.scalar_one_or_none()

    if not rubrica:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este caso no tiene una rúbrica. Use POST para crearla."
        )

    # Validar suma de criterios
    suma_criterios = sum(c.puntaje_maximo for c in payload.criterios)

    if suma_criterios > payload.escala_maxima:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La suma de los criterios ({suma_criterios}) excede la escala máxima ({payload.escala_maxima})"
        )

    # Actualizar datos de la rúbrica
    rubrica.nombre = payload.nombre
    rubrica.descripcion = payload.descripcion
    rubrica.tipo_rubrica = payload.tipo_rubrica
    rubrica.escala_maxima = payload.escala_maxima
    rubrica.publica = payload.publica
    rubrica.permitir_autoevaluacion = payload.permitir_autoevaluacion
    rubrica.vigente = payload.vigente

    # ----------------------
    # Actualizar criterios
    # ----------------------

    # Eliminar criterios actuales
    for criterio in rubrica.criterios:
        await session.delete(criterio)

    rubrica.criterios = []

    # Crear nuevos criterios
    for idx, criterio_data in enumerate(payload.criterios):

        criterio = CriterioRubrica(
            nombre=criterio_data.nombre,
            descripcion=criterio_data.descripcion,
            puntaje_maximo=criterio_data.puntaje_maximo,
            orden=criterio_data.orden if criterio_data.orden else idx
        )

        rubrica.criterios.append(criterio)

    await session.commit()

    # Recargar con relaciones
    result = await session.execute(
        select(Rubrica)
        .options(selectinload(Rubrica.criterios))
        .where(Rubrica.id == rubrica.id)
    )

    rubrica = result.scalar_one()

    return rubrica
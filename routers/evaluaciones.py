from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List
import os
import json
from dotenv import load_dotenv

from typing import Optional

from db_connection import get_session
from orm import Evaluacion, EvaluacionDetalle, Entrega, Rubrica, CriterioRubrica, Usuario
from schemas import (
    EvaluacionIn, EvaluacionOut, EvaluacionDetalle as EvaluacionDetalleSchema,
    EvaluacionIARequest, EvaluacionIAResponse, EvaluacionDetalleOut
)
from auth import get_current_user, require_role

# Cargar variables de entorno
load_dotenv()

router = APIRouter(
    prefix="/evaluaciones",
    tags=["Evaluaciones"]
)



# 📝 ENDPOINTS CRUD (EVALUACIÓN MANUAL)


@router.post("/", response_model=EvaluacionOut, status_code=status.HTTP_201_CREATED)
async def create_evaluacion_manual(
    payload: EvaluacionIn,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    
    # Verificar que la entrega existe
    result = await session.execute(
        select(Entrega).where(Entrega.id == payload.entrega_id)
    )
    entrega = result.scalar_one_or_none()

    if not entrega:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrega no encontrada"
        )

    # Verificar que no exista ya una evaluación
    result = await session.execute(
        select(Evaluacion).where(Evaluacion.entrega_id == payload.entrega_id)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Esta entrega ya tiene una evaluación"
        )

    # Verificar que la rúbrica existe
    result = await session.execute(
        select(Rubrica)
        .options(selectinload(Rubrica.criterios))
        .where(Rubrica.id == payload.rubrica_id)
    )
    rubrica = result.scalar_one_or_none()

    if not rubrica:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rúbrica no encontrada"
        )

    # Validar que todos los criterios estén evaluados
    criterios_ids_rubrica = {c.id for c in rubrica.criterios}
    criterios_ids_evaluacion = {d.criterio_id for d in payload.detalles}

    if criterios_ids_rubrica != criterios_ids_evaluacion:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes evaluar todos los criterios de la rúbrica"
        )

    # Crear evaluación
    evaluacion = Evaluacion(
        entrega_id=payload.entrega_id,
        docente_id=current_user.id,
        rubrica_id=payload.rubrica_id,
        observaciones_text=payload.observaciones_text,
        nota_total=payload.nota_total,
        estado=payload.estado,
        es_privado=payload.es_privado,
        reevaluacion=payload.reevaluacion
    )

    session.add(evaluacion)
    await session.flush()

    # Crear detalles
    for detalle_data in payload.detalles:
        detalle = EvaluacionDetalle(
            evaluacion_id=evaluacion.id,
            criterio_id=detalle_data.criterio_id,
            puntaje_numerico=detalle_data.puntaje_numerico,
            comentario_text=detalle_data.comentario_text
        )
        session.add(detalle)

    # Actualizar estado de la entrega
    entrega.estado = "publicada"

    await session.commit()
    await session.refresh(evaluacion)

    return evaluacion

@router.get("/", response_model=List[EvaluacionOut])
async def list_evaluaciones(
    entrega_id: int = None,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Listar evaluaciones.
    """
    query = select(Evaluacion)

    if current_user.rol == "estudiante":
        query = query.join(Entrega).where(
            Entrega.estudiante_id == current_user.id,
            Evaluacion.es_privado == False
        )

    if entrega_id:
        query = query.where(Evaluacion.entrega_id == entrega_id)

    result = await session.execute(query)
    evaluaciones = result.scalars().all()

    return evaluaciones

@router.get("/{evaluacion_id}", response_model=EvaluacionDetalleSchema)
async def get_evaluacion(
    evaluacion_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener evaluación con detalles de cada criterio.
    """
    result = await session.execute(
        select(Evaluacion)
        .options(
            selectinload(Evaluacion.detalles).selectinload(EvaluacionDetalle.criterio),
            selectinload(Evaluacion.entrega)
        )
        .where(Evaluacion.id == evaluacion_id)
    )
    evaluacion = result.scalar_one_or_none()

    if not evaluacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluación no encontrada"
        )

    if current_user.rol == "estudiante":
        if evaluacion.entrega.estudiante_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver esta evaluación"
            )
        if evaluacion.es_privado:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta evaluación es privada"
            )

    return evaluacion

@router.get("/MisEvaluaciones/{entrega_id}", response_model=Optional[EvaluacionDetalleSchema])
async def get_evaluacion_id(
    entrega_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(get_current_user)
):
    
    
    result = await session.execute(
        select(Evaluacion)
        .options(
            selectinload(Evaluacion.detalles).selectinload(EvaluacionDetalle.criterio),
            selectinload(Evaluacion.entrega)
        )
        .where(Evaluacion.entrega_id == entrega_id)
    )
    evaluacion = result.scalar_one_or_none()

    return evaluacion


@router.put("/{evaluacion_id}")
async def update_evaluacion(
    evaluacion_id: int,
    payload: dict,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    result = await session.execute(
        select(Evaluacion)
        .where(Evaluacion.id == evaluacion_id)
        .options(selectinload(Evaluacion.detalles))
    )
    evaluacion = result.scalar_one_or_none()
    if not evaluacion:
        raise HTTPException(status_code=404, detail="Evaluacion no encontrada")

    evaluacion.nota_total = payload.get("nota_total", evaluacion.nota_total)
    evaluacion.observaciones_text = payload.get("observaciones_text", evaluacion.observaciones_text)
    evaluacion.estado = payload.get("estado", evaluacion.estado)
    evaluacion.docente_id = current_user.id

    for detalle_data in payload.get("detalles", []):
        for detalle in evaluacion.detalles:
            if detalle.criterio_id == detalle_data.get("criterio_id"):
                detalle.puntaje_numerico = detalle_data.get("puntaje_numerico", detalle.puntaje_numerico)
                detalle.comentario_text = detalle_data.get("comentario_text", detalle.comentario_text)
                break

    await session.commit()
    return {
        "message": "Evaluacion confirmada como final",
        "evaluacion_id": evaluacion_id,
        "estado": evaluacion.estado,
        "nota_total": float(evaluacion.nota_total),
        "docente_id": evaluacion.docente_id
    }


@router.post("/evaluar-con-ia/{entrega_id}", response_model=EvaluacionIAResponse)
async def evaluar_con_ia(
    entrega_id: int,
    request: Optional[EvaluacionIARequest] = None,
    # request: EvaluacionIARequest = None,
    session: AsyncSession = Depends(get_session),
    # current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """
    EVALUACIÓN AUTOMÁTICA CON INTELIGENCIA ARTIFICIAL

    Flujo:
    1. Obtiene la entrega del estudiante (campo 'respuesta')
    2. Obtiene la rúbrica del caso con todos sus criterios
    3. Construye un prompt y envía a OpenAI
    4. La IA califica cada criterio de 0 a 5
    5. Guarda la evaluación y detalles en la base de datos

    Requiere: OPENAI_API_KEY en el archivo .env
    """
    try:
        #1. Obtener la entrega con el caso ──
        result = await session.execute(
            select(Entrega)
            .options(selectinload(Entrega.caso))
            .where(Entrega.id == entrega_id)
        )
        entrega = result.scalar_one_or_none()

        if not entrega:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrega no encontrada"
            )

        if not entrega.respuesta or entrega.respuesta.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La entrega no tiene contenido en el campo 'respuesta'"
            )

        #2. Verificar que no esté ya evaluada
        result = await session.execute(
            select(Evaluacion).where(Evaluacion.entrega_id == entrega_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Esta entrega ya tiene una evaluación"
            )

        #3. Obtener la rúbrica del caso con criterios 
        result = await session.execute(
            select(Rubrica)
            .options(selectinload(Rubrica.criterios))
            .where(Rubrica.caso_id == entrega.caso_id)
        )
        rubrica = result.scalar_one_or_none()

        if not rubrica:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El caso '{entrega.caso.titulo}' no tiene rúbrica definida"
            )

        if not rubrica.criterios:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La rúbrica no tiene criterios definidos"
            )

        #4. Preparar las rúbricas como diccionario 
        rubricas_dict = {}
        criterios_map = {}  # Para mapear nombre -> id
        for criterio in rubrica.criterios:
            rubricas_dict[criterio.nombre] = criterio.descripcion or criterio.nombre
            criterios_map[criterio.nombre.lower().strip()] = criterio.id

        #5. Construir el prompt (estilo Wilson)
        prompt = f"""
Eres un docente universitario experto en evaluación de casos de estudio empresariales.

Evalúa la siguiente respuesta de un estudiante usando las rúbricas proporcionadas.

**CASO EMPRESARIAL:**
{entrega.caso.descripcion}

**RESPUESTA DEL ESTUDIANTE:**
\"\"\"{entrega.respuesta}\"\"\"

**RÚBRICAS DE EVALUACIÓN:**
{json.dumps(rubricas_dict, indent=2, ensure_ascii=False)}

**INSTRUCCIONES:**
- Califica cada criterio de 0 a 5 (donde 0 es deficiente y 5 es excelente)
- Sé estricto pero justo en la calificación
- Da retroalimentación constructiva y específica por cada criterio
- Calcula el promedio final (0 a 5)
- Devuelve SOLO un JSON válido con este formato exacto:

{{
  "calificacion_final": <promedio de 0 a 5>,
  "criterios": [
    {{
      "nombre": "<nombre exacto del criterio>",
      "puntaje": <número de 0 a 5>,
      "comentario": "<retroalimentación constructiva>"
    }}
  ],
  "retroalimentacion_general": "<comentario general con recomendaciones de mejora>"
}}
"""

        #6. Llamar a OpenAI
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OPENAI_API_KEY no está configurada en el archivo .env"
            )

        client = OpenAI(api_key=api_key)

        modelo = request.modelo_ia if request else "gpt-4o-mini"
        temperatura = request.temperatura if request else 0.3

        response = client.chat.completions.create(
            model=modelo,
            messages=[
                {
                    "role": "system",
                    "content": "Eres un docente universitario experto en evaluación. Responde SOLO con JSON válido, sin markdown ni texto adicional."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=temperatura
        )

        #7. Procesar respuesta de la IA
        output = response.choices[0].message.content.strip()

        # Limpiar si viene con markdown
        if output.startswith("```"):
            output = output.split("\n", 1)[1] if "\n" in output else output
            if output.endswith("```"):
                output = output[:-3]
            output = output.strip()

        resultado_ia = json.loads(output)

        #8. Crear evaluación en la base de datos
        nota_final = resultado_ia["calificacion_final"]

        evaluacion = Evaluacion(
            entrega_id=entrega_id,
            docente_id=None,  # NULL = evaluación automática por IA
            rubrica_id=rubrica.id,
            observaciones_text=resultado_ia.get(
                "retroalimentacion_general",
                "Evaluación generada automáticamente por IA"
            ),
            nota_total=nota_final,
            estado="publicada",  # El profesor debe revisar y publicar
            es_privado=False,
            reevaluacion=False
        )

        session.add(evaluacion)
        await session.flush()  # Obtener el ID

        #9. Crear detalles por cada criterio
        detalles_out = []
        for criterio_ia in resultado_ia["criterios"]:
            nombre_criterio = criterio_ia["nombre"].lower().strip()

            # Buscar el ID del criterio por nombre
            criterio_id = criterios_map.get(nombre_criterio)

            if not criterio_id:
                # Intentar búsqueda parcial
                for key, value in criterios_map.items():
                    if key in nombre_criterio or nombre_criterio in key:
                        criterio_id = value
                        break

            if not criterio_id:
                # Si no encuentra, usar el primer criterio no asignado
                continue

            detalle = EvaluacionDetalle(
                evaluacion_id=evaluacion.id,
                criterio_id=criterio_id,
                puntaje_numerico=min(criterio_ia["puntaje"], 5.0),  # Máximo 5
                comentario_text=criterio_ia["comentario"]
            )
            session.add(detalle)
            detalles_out.append(EvaluacionDetalleOut(
                id=0,
                evaluacion_id=evaluacion.id,
                criterio_id=criterio_id,
                puntaje_numerico=criterio_ia["puntaje"],
                comentario_text=criterio_ia["comentario"]
            ))

        #10. Actualizar estado de la entrega
        entrega.estado = "revisada"

        await session.commit()
        await session.refresh(evaluacion)

        return EvaluacionIAResponse(
            evaluacion_id=evaluacion.id,
            nota_total=evaluacion.nota_total,
            detalles=detalles_out,
            mensaje=f"Evaluación completada con IA ({modelo}). Estado: publicada."
        )

    except HTTPException:
        raise
    except json.JSONDecodeError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La IA no devolvió un JSON válido. Intenta de nuevo."
        )
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado: {str(e)}"
        )
# routers/carga_caso.py
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import os
import json
import tempfile
from dotenv import load_dotenv

from db_connection import get_session
from orm import Usuario
from auth import get_current_user, require_role
from sqlalchemy import select

load_dotenv()

router = APIRouter(
    prefix="/carga-caso",
    tags=["Carga de Caso con IA"]
)


def extraer_texto_docx(file_path: str) -> str:
    """Extrae texto de un archivo Word"""
    from docx import Document
    doc = Document(file_path)
    texto = []
    for para in doc.paragraphs:
        if para.text.strip():
            texto.append(para.text.strip())
    # También extraer texto de tablas
    for table in doc.tables:
        for row in table.rows:
            fila = []
            for cell in row.cells:
                if cell.text.strip():
                    fila.append(cell.text.strip())
            if fila:
                texto.append(" | ".join(fila))
    return "\n".join(texto)


def extraer_texto_pdf(file_path: str) -> str:
    """Extrae texto de un archivo PDF"""
    from PyPDF2 import PdfReader
    reader = PdfReader(file_path)
    texto = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            texto.append(page_text.strip())
    return "\n".join(texto)


@router.post("/analizar-documento")
async def analizar_documento(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """
    ANALIZAR DOCUMENTO PARA CREAR CASO DE ESTUDIO

    Flujo:
    1. El profesor sube un archivo Word (.docx) o PDF (.pdf)
    2. Se extrae el texto del documento
    3. Se envía a OpenAI para que identifique:
    - Título del caso
    - Descripción del caso
    - Criterios de rúbrica (extraídos o sugeridos)
    4. Retorna los datos para pre-llenar el formulario

    El profesor revisa, ajusta y confirma antes de guardar.
    """
    #1. Validar tipo de archivo
    if not archivo.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se proporcionó un archivo"
        )

    extension = archivo.filename.lower().split(".")[-1]
    if extension not in ["docx", "pdf"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se aceptan archivos .docx o .pdf"
        )

    #2. Guardar archivo temporalmente
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{extension}") as tmp:
            contenido = await archivo.read()
            tmp.write(contenido)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el archivo: {str(e)}"
        )

    #3. Extraer texto del documento
    try:
        if extension == "docx":
            texto_documento = extraer_texto_docx(tmp_path)
        else:
            texto_documento = extraer_texto_pdf(tmp_path)
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al leer el archivo: {str(e)}"
        )
    finally:
        # Limpiar archivo temporal
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    if not texto_documento.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo extraer texto del documento. Verifica que no esté vacío o sea una imagen escaneada."
        )

    # Limitar texto para no exceder tokens de OpenAI
    texto_limitado = texto_documento[:8000]

    #4. Enviar a OpenAI para análisis
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OPENAI_API_KEY no está configurada en el archivo .env"
        )

    client = OpenAI(api_key=api_key)

    prompt = f"""
Eres un experto en diseño curricular y evaluación académica universitaria.

Analiza el siguiente documento académico y extrae la información para crear un caso de estudio en una plataforma educativa.

**DOCUMENTO:**
\"\"\"{texto_limitado}\"\"\"

**INSTRUCCIONES:**
1. Identifica el TÍTULO del caso de estudio (breve y descriptivo)
2. Extrae o redacta una DESCRIPCIÓN clara del caso (qué debe hacer el estudiante, contexto del problema)
3. Si el documento contiene una RÚBRICA de evaluación, extrae los criterios exactos
4. Si NO contiene rúbrica, sugiere entre 3 y 5 criterios de evaluación apropiados para el caso

**IMPORTANTE:**
- Cada criterio debe tener: nombre corto, descripción clara, y puntaje máximo de 5.0
- La escala de calificación es de 0 a 5
- Los criterios deben ser medibles y específicos al contenido del caso

**Devuelve SOLO un JSON válido con este formato exacto:**
{{
  "titulo": "<título del caso>",
  "descripcion": "<descripción del caso para el estudiante>",
  "rubrica_detectada": true/false,
  "nombre_rubrica": "<nombre de la rúbrica>",
  "descripcion_rubrica": "<descripción de la rúbrica>",
  "criterios": [
    {{
      "nombre": "<nombre corto del criterio>",
      "descripcion": "<qué se evalúa>",
      "puntaje_maximo": 5.0,
      "orden": 1
    }}
  ]
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en diseño curricular universitario. Responde SOLO con JSON válido, sin markdown ni texto adicional."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        output = response.choices[0].message.content.strip()

        # Limpiar si viene con markdown
        if output.startswith("```"):
            output = output.split("\n", 1)[1] if "\n" in output else output
            if output.endswith("```"):
                output = output[:-3]
            output = output.strip()

        resultado = json.loads(output)

        return {
            "mensaje": "Documento analizado exitosamente",
            "archivo_nombre": archivo.filename,
            "datos_extraidos": resultado
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La IA no devolvió un JSON válido. Intenta de nuevo."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al analizar con IA: {str(e)}"
        )
    
from pydantic import BaseModel, Field
from typing import List
from orm import Caso, Rubrica, CriterioRubrica


# ── Schemas para confirmar y guardar ──

class CriterioConfirmado(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: str
    puntaje_maximo: float = Field(default=5.0, gt=0, le=5)
    orden: int = Field(default=0, ge=0)

class CasoConfirmado(BaseModel):
    titulo: str = Field(..., max_length=200)
    descripcion: str
    nombre_rubrica: str = Field(..., max_length=100)
    descripcion_rubrica: Optional[str] = None
    escala_maxima: float = Field(default=25.0)
    criterios: List[CriterioConfirmado] = Field(..., min_length=1)
    competencias_ids: List[int] = Field(default_factory=list)
    programas_ids: List[int] = Field(default_factory=list)


@router.post("/confirmar-caso")
async def confirmar_caso(
    payload: CasoConfirmado,
    session: AsyncSession = Depends(get_session),
    current_user: Usuario = Depends(require_role("profesor", "coordinador"))
):
    """
    CONFIRMAR Y GUARDAR CASO ANALIZADO POR IA

    Flujo:
    1. El profesor revisó los datos sugeridos por la IA
    2. Ajustó lo que necesitaba (título, descripción, criterios)
    3. Confirma y este endpoint guarda todo en la BD:
    - CASO (título + descripción)
    - RUBRICA (nombre + descripción)
    - CRITERIO_RUBRICA (cada criterio)
    """
    try:
        #1. Crear el caso
        caso = Caso(
            titulo=payload.titulo,
            descripcion=payload.descripcion,
            creador_id=current_user.id
        )
        session.add(caso)
        await session.flush()  # Obtener caso.id

        #2. Asociar competencias si se enviaron
        if payload.competencias_ids:
            from orm import Competencia
            for comp_id in payload.competencias_ids:
                result = await session.execute(
                    select(Competencia).where(Competencia.id == comp_id)
                )
                competencia = result.scalar_one_or_none()
                if competencia:
                    caso.competencias.append(competencia)

        #3. Asociar programas si se enviaron
        if payload.programas_ids:
            from orm import Programa
            for prog_id in payload.programas_ids:
                result = await session.execute(
                    select(Programa).where(Programa.id == prog_id)
                )
                programa = result.scalar_one_or_none()
                if programa:
                    caso.programas.append(programa)

        #4. Crear la rúbrica
        rubrica = Rubrica(
            caso_id=caso.id,
            docente_id=current_user.id,
            nombre=payload.nombre_rubrica,
            descripcion=payload.descripcion_rubrica,
            vigente=True,
            tipo_rubrica="analitica",
            escala_maxima=payload.escala_maxima,
            publica=True,
            permitir_autoevaluacion=False
        )
        session.add(rubrica)
        await session.flush()  # Obtener rubrica.id

        #5. Crear los criterios
        criterios_creados = []
        for criterio_data in payload.criterios:
            criterio = CriterioRubrica(
                rubrica_id=rubrica.id,
                nombre=criterio_data.nombre,
                descripcion=criterio_data.descripcion,
                puntaje_maximo=criterio_data.puntaje_maximo,
                orden=criterio_data.orden
            )
            session.add(criterio)
            criterios_creados.append({
                "nombre": criterio_data.nombre,
                "descripcion": criterio_data.descripcion,
                "puntaje_maximo": criterio_data.puntaje_maximo,
                "orden": criterio_data.orden
            })

        await session.commit()
        await session.refresh(caso)
        await session.refresh(rubrica)

        return {
            "mensaje": "Caso creado exitosamente con rúbrica y criterios",
            "caso": {
                "id": caso.id,
                "titulo": caso.titulo,
                "descripcion": caso.descripcion,
                "creador_id": caso.creador_id
            },
            "rubrica": {
                "id": rubrica.id,
                "nombre": rubrica.nombre,
                "escala_maxima": float(rubrica.escala_maxima),
                "criterios": criterios_creados
            }
        }

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al guardar el caso: {str(e)}"
        )
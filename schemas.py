# schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

class UsuarioIn(BaseModel):
    nombre_usuario: str = Field(..., min_length=3, max_length=50)
    correo_electronico: EmailStr
    contrasena: str = Field(..., min_length=3, max_length=73) 
    rol: str = Field(default="estudiante", pattern="^(estudiante|profesor|coordinador)$")

class UsuarioOut(BaseModel):
    id: int
    nombre_usuario: str
    correo_electronico: EmailStr
    rol: str
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

# === PERFIL EGRESO ===
class PerfilEgresoBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)

class PerfilEgresoIn(PerfilEgresoBase):
    pass

class PerfilEgresoOut(PerfilEgresoBase):
    id: int
    
    class Config:
        from_attributes = True


# === PROGRAMA ===
class ProgramaBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    codigo: str = Field(..., max_length=20)
    descripcion: Optional[str] = Field(None, max_length=500)
    perfil_egreso_id: Optional[int] = None

class ProgramaIn(ProgramaBase):
    pass

class ProgramaOut(ProgramaBase):
    id: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True


# === COMPETENCIA ===
class CompetenciaBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)

class CompetenciaIn(CompetenciaBase):
    pass

class CompetenciaOut(CompetenciaBase):
    id: int
    
    class Config:
        from_attributes = True


# === RESULTADO APRENDIZAJE ===
class ResultadoAprendizajeBase(BaseModel):
    perfil_egreso_id: int
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = Field(None, max_length=500)

class ResultadoAprendizajeIn(ResultadoAprendizajeBase):
    pass

class ResultadoAprendizajeOut(ResultadoAprendizajeBase):
    id: int
    
    class Config:
        from_attributes = True

# === CRITERIO RUBRICA ===
class CriterioRubricaBase(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    puntaje_maximo: float = Field(..., gt=0, le=100)
    orden: int = Field(default=0, ge=0)

class CriterioRubricaIn(CriterioRubricaBase):
    pass

class CriterioRubricaOut(CriterioRubricaBase):
    id: int
    rubrica_id: int
    
    class Config:
        from_attributes = True

# === RUBRICA ===
class RubricaBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    tipo_rubrica: str = Field(default="default", max_length=50)
    escala_maxima: float = Field(default=100.0, gt=0, le=100)
    publica: bool = Field(default=False)
    permitir_autoevaluacion: bool = Field(default=False)
    vigente: bool = Field(default=True)

class RubricaIn(RubricaBase):
    criterios: List[CriterioRubricaIn] = Field(..., min_length=1)

class RubricaOut(RubricaBase):
    id: int
    caso_id: int
    docente_id: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class RubricaDetalle(RubricaOut):
    """Rúbrica con criterios incluidos"""
    criterios: List[CriterioRubricaOut] = []
    
    class Config:
        from_attributes = True

# === CASO ===
class CasoBase(BaseModel):
    titulo: str = Field(..., max_length=200)
    descripcion: str

class CasoIn(CasoBase):
    competencias_ids: List[int] = Field(default_factory=list)
    programas_ids: List[int] = Field(default_factory=list)

class CasoOut(CasoBase):
    id: int
    fecha_creacion: datetime
    creador_id: int
    
    class Config:
        from_attributes = True

class CasoDetalle(CasoOut):
    """Caso con relaciones incluidas"""
    competencias: List[CompetenciaOut] = []
    programas: List[ProgramaOut] = []
    
    class Config:
        from_attributes = True

# === ENTREGA ===
class EntregaBase(BaseModel):
    respuesta: str
    url_archivo: Optional[str] = Field(None, max_length=500)
    tiempo_dedicado: Optional[int] = Field(None, ge=0, description="Tiempo en minutos")
    retroalimentacion_estudiante: Optional[str] = None

class EntregaIn(EntregaBase):
    caso_id: int = Field(..., gt=0)

class EntregaUpdate(BaseModel):
    """Para actualizar entregas existentes"""
    titulo: Optional[str] = Field(None, max_length=200)
    url_archivo: Optional[str] = Field(None, max_length=500)
    tiempo_dedicado: Optional[int] = Field(None, ge=0)
    retroalimentacion_estudiante: Optional[str] = None

class EntregaOut(EntregaBase):
    id: int
    caso_id: int
    estudiante_id: int
    estado: str
    fecha_entrega: datetime
    
    class Config:
        from_attributes = True

class EntregaDetalle(EntregaOut):
    """Entrega con información del caso y estudiante"""
    # Aquí podrías incluir info del caso y estudiante si lo necesitas
    pass

# === EVALUACION DETALLE ===
class EvaluacionDetalleBase(BaseModel):
    criterio_id: int = Field(..., gt=0)
    puntaje_numerico: float = Field(..., ge=0, le=100)
    comentario_text: Optional[str] = None

class EvaluacionDetalleIn(EvaluacionDetalleBase):
    pass

class EvaluacionDetalleOut(EvaluacionDetalleBase):
    id: int
    evaluacion_id: int
    
    class Config:
        from_attributes = True

class EvaluacionDetalleConCriterio(EvaluacionDetalleOut):
    """Detalle con información del criterio"""
    criterio: CriterioRubricaOut
    
    class Config:
        from_attributes = True

# === EVALUACION ===
class EvaluacionBase(BaseModel):
    observaciones_text: Optional[str] = None
    nota_total: float = Field(..., ge=0, le=100)
    estado: str = Field(default="borrador", pattern="^(borrador|publicada|revisada)$")
    es_privado: bool = Field(default=False)
    reevaluacion: bool = Field(default=False)

class EvaluacionIn(EvaluacionBase):
    entrega_id: int = Field(..., gt=0)
    rubrica_id: int = Field(..., gt=0)
    detalles: List[EvaluacionDetalleIn] = Field(..., min_length=1)

class EvaluacionOut(EvaluacionBase):
    id: int
    entrega_id: int
    docente_id: Optional[int] = None
    rubrica_id: int
    fecha_evaluacion: datetime
    
    class Config:
        from_attributes = True

class EvaluacionDetalle(EvaluacionOut):
    """Evaluación con detalles por criterio"""
    detalles: List[EvaluacionDetalleConCriterio] = []
    
    class Config:
        from_attributes = True

        # === COMENTARIO ENTREGA ===
class ComentarioBase(BaseModel):
    comentario_text: str = Field(..., min_length=1)
    es_privado: bool = Field(default=False)

class ComentarioIn(ComentarioBase):
    entrega_id: int = Field(..., gt=0)

class ComentarioOut(ComentarioBase):
    id: int
    entrega_id: int
    usuario_id: int
    fecha_timestamp: datetime
    
    class Config:
        from_attributes = True

class ComentarioConUsuario(ComentarioOut):
    """Comentario con información del usuario"""
    usuario: UsuarioOut
    
    class Config:
        from_attributes = True

        # === ARCHIVO CASO ===
class ArchivoBase(BaseModel):
    nombre_archivo: str = Field(..., max_length=255)
    url_archivo: str = Field(..., max_length=500)
    tipo_archivo: str = Field(..., max_length=50)
    descripcion: Optional[str] = None

class ArchivoIn(ArchivoBase):
    caso_id: int = Field(..., gt=0)

class ArchivoOut(ArchivoBase):
    id: int
    caso_id: int
    fecha_subida: datetime
    
    class Config:
        from_attributes = True

        # === NOTIFICACION ===
class NotificacionBase(BaseModel):
    titulo: str = Field(..., max_length=200)
    mensaje_text: str = Field(..., min_length=1)
    url_accion: Optional[str] = Field(None, max_length=300)

class NotificacionIn(NotificacionBase):
    usuario_id: int = Field(..., gt=0)

class NotificacionOut(NotificacionBase):
    id: int
    usuario_id: int
    leida: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class NotificacionUpdate(BaseModel):
    """Para marcar como leída"""
    leida: bool

# === IA EVALUATION REQUEST ===
class EvaluacionIARequest(BaseModel):
    """Request para evaluación automática con IA"""
    entrega_id: int = Field(..., gt=0)
    modelo_ia: str = Field(default="gpt-4", description="Modelo de IA a usar")
    temperatura: float = Field(default=0.3, ge=0, le=1, description="Creatividad del modelo")

class EvaluacionIAResponse(BaseModel):
    """Response de evaluación automática"""
    evaluacion_id: int
    nota_total: float
    detalles: List[EvaluacionDetalleOut]
    mensaje: str = "Evaluación completada exitosamente"

    
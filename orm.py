# orm.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey, Table, func
from sqlalchemy.orm import Mapped, mapped_column, relationship,  DeclarativeBase
from datetime import datetime
from typing import List, Optional

from db_connection import Base

# =================== TABLAS DE ASOCIACIÓN (Many-to-Many) ===================

resultado_competencia = Table(
    'RESULTADO_COMPETENCIA',
    Base.metadata,
    Column('resultado_id', Integer, ForeignKey('RESULTADO_APRENDIZAJE.id', ondelete='CASCADE'), primary_key=True),
    Column('competencia_id', Integer, ForeignKey('COMPETENCIA.id', ondelete='CASCADE'), primary_key=True)
)

caso_competencia = Table(
    'CASO_COMPETENCIA',
    Base.metadata,
    Column('caso_id', Integer, ForeignKey('CASO.id', ondelete='CASCADE'), primary_key=True),
    Column('competencia_id', Integer, ForeignKey('COMPETENCIA.id', ondelete='CASCADE'), primary_key=True)
)

programa_caso = Table(
    'PROGRAMA_CASO',
    Base.metadata,
    Column('programa_id', Integer, ForeignKey('PROGRAMA.id', ondelete='CASCADE'), primary_key=True),
    Column('caso_id', Integer, ForeignKey('CASO.id', ondelete='CASCADE'), primary_key=True)
)


# =================== USUARIO ===================

class Usuario(Base):
    __tablename__ = "USUARIO"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre_usuario: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    correo_electronico: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    contrasena_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False, default="estudiante")
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    # Relaciones
    casos_creados: Mapped[List["Caso"]] = relationship("Caso", back_populates="creador", foreign_keys="Caso.creador_id")
    rubricas_creadas: Mapped[List["Rubrica"]] = relationship("Rubrica", foreign_keys="Rubrica.docente_id", back_populates="docente")
    entregas_realizadas: Mapped[List["Entrega"]] = relationship("Entrega", foreign_keys="Entrega.estudiante_id", back_populates="estudiante")
    evaluaciones_realizadas: Mapped[List["Evaluacion"]] = relationship("Evaluacion", foreign_keys="Evaluacion.docente_id", back_populates="docente")
    comentarios_realizados: Mapped[List["ComentarioEntrega"]] = relationship("ComentarioEntrega", back_populates="usuario", cascade="all, delete-orphan")
    notificaciones: Mapped[List["Notificacion"]] = relationship("Notificacion", back_populates="usuario", cascade="all, delete-orphan")

# =================== PERFIL EGRESO ===================

class PerfilEgreso(Base):
    __tablename__ = "PERFIL_EGRESO"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relaciones
    programas: Mapped[List["Programa"]] = relationship("Programa", back_populates="perfil_egreso")
    resultados_aprendizaje: Mapped[List["ResultadoAprendizaje"]] = relationship("ResultadoAprendizaje", back_populates="perfil_egreso")


# =================== COMPETENCIA ===================

class Competencia(Base):
    __tablename__ = "COMPETENCIA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relaciones many-to-many
    resultados: Mapped[List["ResultadoAprendizaje"]] = relationship(
        "ResultadoAprendizaje",
        secondary=resultado_competencia,
        back_populates="competencias"
    )
    casos: Mapped[List["Caso"]] = relationship(
        "Caso",
        secondary=caso_competencia,
        back_populates="competencias"
    )


# =================== PROGRAMA ===================

class Programa(Base):
    __tablename__ = "PROGRAMA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    perfil_egreso_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('PERFIL_EGRESO.id'), nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    # Relaciones
    perfil_egreso: Mapped[Optional["PerfilEgreso"]] = relationship("PerfilEgreso", back_populates="programas")
    casos: Mapped[List["Caso"]] = relationship(
        "Caso",
        secondary=programa_caso,
        back_populates="programas"
    )


# =================== RESULTADO APRENDIZAJE ===================

class ResultadoAprendizaje(Base):
    __tablename__ = "RESULTADO_APRENDIZAJE"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    perfil_egreso_id: Mapped[int] = mapped_column(Integer, ForeignKey('PERFIL_EGRESO.id'), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Relaciones
    perfil_egreso: Mapped["PerfilEgreso"] = relationship("PerfilEgreso", back_populates="resultados_aprendizaje")
    competencias: Mapped[List["Competencia"]] = relationship(
        "Competencia",
        secondary=resultado_competencia,
        back_populates="resultados"
    )


# =================== CASO ===================

class Caso(Base):
    __tablename__ = "CASO"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    creador_id: Mapped[int] = mapped_column(Integer, ForeignKey('USUARIO.id'), nullable=False)
    
    # Relaciones
    creador: Mapped["Usuario"] = relationship("Usuario", back_populates="casos_creados", foreign_keys=[creador_id])
    competencias: Mapped[List["Competencia"]] = relationship(
        "Competencia",
        secondary=caso_competencia,
        back_populates="casos",
        lazy="selectin"
    )
    programas: Mapped[List["Programa"]] = relationship(
        "Programa",
        secondary=programa_caso,
        back_populates="casos",
        lazy="selectin"
    )
    rubrica: Mapped[Optional["Rubrica"]] = relationship(
        "Rubrica", 
        back_populates="caso", 
        uselist=False, 
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    entregas: Mapped[List["Entrega"]] = relationship(
        "Entrega",
        back_populates="caso",
        cascade="all, delete-orphan"
    )
    archivos: Mapped[List["ArchivoCaso"]] = relationship(
        "ArchivoCaso",
        back_populates="caso",
        cascade="all, delete-orphan"
    )

# =================== RUBRICA ===================

class Rubrica(Base):
    __tablename__ = "RUBRICA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(Integer, ForeignKey('CASO.id', ondelete='CASCADE'), nullable=False, unique=True)
    docente_id: Mapped[int] = mapped_column(Integer, ForeignKey('USUARIO.id'), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    vigente: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    tipo_rubrica: Mapped[str] = mapped_column(String(50), nullable=False, default="default")
    escala_maxima: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=100.0)
    publica: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    permitir_autoevaluacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relaciones
    caso: Mapped["Caso"] = relationship("Caso", back_populates="rubrica")
    docente: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[docente_id])
    criterios: Mapped[List["CriterioRubrica"]] = relationship(
        "CriterioRubrica", 
        back_populates="rubrica", 
        cascade="all, delete-orphan",
        lazy="selectin"
    )

class CriterioRubrica(Base):
    __tablename__ = "CRITERIO_RUBRICA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rubrica_id: Mapped[int] = mapped_column(Integer, ForeignKey('RUBRICA.id', ondelete='CASCADE'), nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    puntaje_maximo: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Relaciones
    rubrica: Mapped["Rubrica"] = relationship("Rubrica", back_populates="criterios")
    evaluaciones_detalle: Mapped[List["EvaluacionDetalle"]] = relationship(
        "EvaluacionDetalle", 
        back_populates="criterio",
        cascade="all, delete-orphan"
    )


# =================== ENTREGA ===================

class Entrega(Base):
    __tablename__ = "ENTREGA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(Integer, ForeignKey('CASO.id', ondelete='CASCADE'), nullable=False)
    estudiante_id: Mapped[int] = mapped_column(Integer, ForeignKey('USUARIO.id'), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    fecha_entrega: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    respuesta: Mapped[str] = mapped_column(Text, nullable=False)
    json_respuestas: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retroalimentacion_estudiante: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relaciones
    caso: Mapped["Caso"] = relationship("Caso", back_populates="entregas")
    estudiante: Mapped["Usuario"] = relationship("Usuario", foreign_keys=[estudiante_id], back_populates="entregas_realizadas")
    evaluacion: Mapped[Optional["Evaluacion"]] = relationship(
        "Evaluacion", 
        back_populates="entrega", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    comentarios: Mapped[List["ComentarioEntrega"]] = relationship(
        "ComentarioEntrega", 
        back_populates="entrega",
        cascade="all, delete-orphan"
    )


# =================== EVALUACION ===================

class Evaluacion(Base):
    __tablename__ = "EVALUACION"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entrega_id: Mapped[int] = mapped_column(Integer, ForeignKey('ENTREGA.id', ondelete='CASCADE'), nullable=False, unique=True)
    docente_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('USUARIO.id'), nullable=True)
    rubrica_id: Mapped[int] = mapped_column(Integer, ForeignKey('RUBRICA.id'), nullable=False)
    fecha_evaluacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    observaciones_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nota_total: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="borrador")
    es_privado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reevaluacion: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relaciones
    entrega: Mapped["Entrega"] = relationship("Entrega", back_populates="evaluacion")
    docente: Mapped[Optional["Usuario"]] = relationship(
        "Usuario", 
        foreign_keys=[docente_id],
        back_populates="evaluaciones_realizadas"
    )
    rubrica: Mapped["Rubrica"] = relationship("Rubrica")
    detalles: Mapped[List["EvaluacionDetalle"]] = relationship(
        "EvaluacionDetalle", 
        back_populates="evaluacion",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
# =================== EVALUACION DETALLE ===================

class EvaluacionDetalle(Base):
    __tablename__ = "EVALUACION_DETALLE"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluacion_id: Mapped[int] = mapped_column(Integer, ForeignKey('EVALUACION.id', ondelete='CASCADE'), nullable=False)
    criterio_id: Mapped[int] = mapped_column(Integer, ForeignKey('CRITERIO_RUBRICA.id'), nullable=False)
    puntaje_numerico: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    comentario_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relaciones
    evaluacion: Mapped["Evaluacion"] = relationship("Evaluacion", back_populates="detalles")
    criterio: Mapped["CriterioRubrica"] = relationship("CriterioRubrica", back_populates="evaluaciones_detalle")

# =================== COMENTARIO ENTREGA ===================

class ComentarioEntrega(Base):
    __tablename__ = "COMENTARIO_ENTREGA"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entrega_id: Mapped[int] = mapped_column(Integer, ForeignKey('ENTREGA.id', ondelete='CASCADE'), nullable=False)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey('USUARIO.id'), nullable=False)
    comentario_text: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    es_privado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # Relaciones
    entrega: Mapped["Entrega"] = relationship("Entrega", back_populates="comentarios")
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        back_populates="comentarios_realizados"
    )


# =================== ARCHIVO CASO ===================

class ArchivoCaso(Base):
    __tablename__ = "ARCHIVO_CASO"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    caso_id: Mapped[int] = mapped_column(Integer, ForeignKey('CASO.id', ondelete='CASCADE'), nullable=False)
    nombre_archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    url_archivo: Mapped[str] = mapped_column(String(500), nullable=False)
    tipo_archivo: Mapped[str] = mapped_column(String(50), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fecha_subida: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    
    # Relaciones
    caso: Mapped["Caso"] = relationship("Caso", back_populates="archivos")


# =================== NOTIFICACION ===================

class Notificacion(Base):
    __tablename__ = "NOTIFICACION"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(Integer, ForeignKey('USUARIO.id', ondelete='CASCADE'), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje_text: Mapped[str] = mapped_column(Text, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    url_accion: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    
    # Relaciones
    usuario: Mapped["Usuario"] = relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        back_populates="notificaciones"
    )



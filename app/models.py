from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class AuditMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Empresa(AuditMixin, Base):
    __tablename__ = "empresa"
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    areas: Mapped[list[Area]] = relationship(back_populates="empresa")


class Area(AuditMixin, Base):
    __tablename__ = "area"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_area_empresa_codigo"),)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id", ondelete="RESTRICT"), nullable=False)
    empresa: Mapped[Empresa] = relationship(back_populates="areas")
    departamentos: Mapped[list[Departamento]] = relationship(back_populates="area")


class Departamento(AuditMixin, Base):
    __tablename__ = "departamento"
    __table_args__ = (UniqueConstraint("area_id", "codigo", name="uq_departamento_area_codigo"),)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    area_id: Mapped[int] = mapped_column(ForeignKey("area.id", ondelete="RESTRICT"), nullable=False)
    area: Mapped[Area] = relationship(back_populates="departamentos")
    secciones: Mapped[list[Seccion]] = relationship(back_populates="departamento")


class Seccion(AuditMixin, Base):
    __tablename__ = "seccion"
    __table_args__ = (UniqueConstraint("departamento_id", "codigo", name="uq_seccion_departamento_codigo"),)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    departamento_id: Mapped[int] = mapped_column(ForeignKey("departamento.id", ondelete="RESTRICT"), nullable=False)
    departamento: Mapped[Departamento] = relationship(back_populates="secciones")
    puestos: Mapped[list[Puesto]] = relationship(back_populates="seccion")


class Puesto(AuditMixin, Base):
    __tablename__ = "puesto"
    __table_args__ = (UniqueConstraint("seccion_id", "codigo", name="uq_puesto_seccion_codigo"),)
    codigo: Mapped[str] = mapped_column(String(40), nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    seccion_id: Mapped[int] = mapped_column(ForeignKey("seccion.id", ondelete="RESTRICT"), nullable=False)
    seccion: Mapped[Seccion] = relationship(back_populates="puestos")
    usuarios: Mapped[list[Usuario]] = relationship(back_populates="puesto")


class Usuario(AuditMixin, Base):
    __tablename__ = "usuario"
    __table_args__ = (CheckConstraint("rol IN ('administrador','consulta')", name="ck_usuario_rol"),)
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    login: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    puesto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("puesto.id", ondelete="RESTRICT"))
    puesto: Mapped[Optional[Puesto]] = relationship(back_populates="usuarios")
    sesiones: Mapped[list[Sesion]] = relationship(back_populates="usuario")


class Sesion(Base):
    __tablename__ = "sesion"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), nullable=False)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revocada_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    usuario: Mapped[Usuario] = relationship(back_populates="sesiones")


class CatalogoBase(AuditMixin):
    codigo: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)


class ClaseServicio(CatalogoBase, Base):
    __tablename__ = "clase_servicio"


class Criticidad(CatalogoBase, Base):
    __tablename__ = "criticidad"


class TipoServicio(CatalogoBase, Base):
    __tablename__ = "tipo_servicio"


class ServicioNivel1(AuditMixin, Base):
    __tablename__ = "servicio_nivel1"
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(240), nullable=False)
    origen_hoja: Mapped[Optional[str]] = mapped_column(String(120))
    origen_fila: Mapped[Optional[int]] = mapped_column()
    origen_rango: Mapped[Optional[str]] = mapped_column(String(80))


class ServicioNivel2(AuditMixin, Base):
    __tablename__ = "servicio_nivel2"
    __table_args__ = (CheckConstraint("minimo IS NULL OR maximo IS NULL OR minimo <= maximo", name="ck_servicio_min_max"),)
    codigo: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    codigo_original: Mapped[Optional[str]] = mapped_column(String(60))
    nombre: Mapped[str] = mapped_column(String(240), nullable=False)
    nivel1_id: Mapped[int] = mapped_column(ForeignKey("servicio_nivel1.id", ondelete="RESTRICT"), nullable=False)
    indicador_activo_excel: Mapped[Optional[str]] = mapped_column(String(40))
    clase_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clase_servicio.id", ondelete="RESTRICT"))
    criticidad_id: Mapped[Optional[int]] = mapped_column(ForeignKey("criticidad.id", ondelete="RESTRICT"))
    tipo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tipo_servicio.id", ondelete="RESTRICT"))
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    metrica: Mapped[Optional[str]] = mapped_column(String(240))
    minimo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    maximo: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    estado_revision: Mapped[str] = mapped_column(String(30), default="completo", nullable=False)
    seccion_responsable_id: Mapped[Optional[int]] = mapped_column(ForeignKey("seccion.id", ondelete="RESTRICT"))
    usuario_responsable_id: Mapped[Optional[int]] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    origen_hoja: Mapped[Optional[str]] = mapped_column(String(120))
    origen_fila: Mapped[Optional[int]] = mapped_column()
    origen_rango: Mapped[Optional[str]] = mapped_column(String(80))
    nivel1: Mapped[ServicioNivel1] = relationship()
    clase: Mapped[Optional[ClaseServicio]] = relationship()
    criticidad: Mapped[Optional[Criticidad]] = relationship()
    tipo: Mapped[Optional[TipoServicio]] = relationship()
    seccion_responsable: Mapped[Optional[Seccion]] = relationship()
    usuario_responsable: Mapped[Optional[Usuario]] = relationship()


class ImportacionLote(Base):
    __tablename__ = "importacion_lote"
    id: Mapped[int] = mapped_column(primary_key=True)
    archivo: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    iniciada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finalizada_en: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    creados: Mapped[int] = mapped_column(default=0)
    actualizados: Mapped[int] = mapped_column(default=0)
    omitidos: Mapped[int] = mapped_column(default=0)
    observados: Mapped[int] = mapped_column(default=0)
    estado: Mapped[str] = mapped_column(String(30), default="iniciada", nullable=False)


class ImportacionObservacion(Base):
    __tablename__ = "importacion_observacion"
    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(ForeignKey("importacion_lote.id", ondelete="CASCADE"), nullable=False)
    hoja: Mapped[str] = mapped_column(String(120), nullable=False)
    fila: Mapped[Optional[int]] = mapped_column()
    rango_origen: Mapped[Optional[str]] = mapped_column(String(80))
    codigo: Mapped[Optional[str]] = mapped_column(String(60))
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    detalle: Mapped[str] = mapped_column(Text, nullable=False)
    valor_original: Mapped[Optional[str]] = mapped_column(Text)
    valor_canonico: Mapped[Optional[str]] = mapped_column(Text)

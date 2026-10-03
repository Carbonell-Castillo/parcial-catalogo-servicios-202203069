from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=200)

class OrgIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=160)
    parent_id: int | None = None

class OrgUpdate(BaseModel):
    codigo: str | None = Field(None, min_length=1, max_length=40)
    nombre: str | None = Field(None, min_length=1, max_length=160)
    parent_id: int | None = None
    activo: bool | None = None

class UserIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=160)
    login: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=10, max_length=200)
    rol: Literal["administrador", "consulta"]
    puesto_id: int | None = None

class UserUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=160)
    login: str | None = Field(None, min_length=3, max_length=254)
    password: str | None = Field(None, min_length=10, max_length=200)
    rol: Literal["administrador", "consulta"] | None = None
    puesto_id: int | None = None
    activo: bool | None = None

class CatalogIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=160)

class ServiceN1In(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    nombre: str = Field(min_length=1, max_length=240)

class ServiceN2In(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    nombre: str = Field(min_length=1, max_length=240)
    nivel1_id: int
    indicador_activo_excel: str | None = Field(None, max_length=40)
    clase_id: int | None = None
    criticidad_id: int | None = None
    tipo_id: int | None = None
    descripcion: str | None = None
    metrica: str | None = Field(None, max_length=240)
    minimo: Decimal | None = None
    maximo: Decimal | None = None
    estado_revision: Literal["completo", "pendiente"] = "completo"
    seccion_responsable_id: int | None = None
    usuario_responsable_id: int | None = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.minimo is not None and self.maximo is not None and self.minimo > self.maximo:
            raise ValueError("mínimo no puede ser mayor que máximo")
        if self.usuario_responsable_id and not self.seccion_responsable_id:
            raise ValueError("un usuario responsable requiere una sección responsable")
        return self

class ServiceN2Update(BaseModel):
    codigo: str | None = Field(None, min_length=1, max_length=60)
    nombre: str | None = Field(None, min_length=1, max_length=240)
    nivel1_id: int | None = None
    indicador_activo_excel: str | None = Field(None, max_length=40)
    clase_id: int | None = None
    criticidad_id: int | None = None
    tipo_id: int | None = None
    descripcion: str | None = None
    metrica: str | None = Field(None, max_length=240)
    minimo: Decimal | None = None
    maximo: Decimal | None = None
    estado_revision: Literal["completo", "pendiente"] | None = None
    seccion_responsable_id: int | None = None
    usuario_responsable_id: int | None = None
    activo: bool | None = None


from __future__ import annotations

import hmac
from datetime import datetime
import os
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.importer import import_excel
from app.models import (
    Area, ClaseServicio, Criticidad, Departamento, Empresa, ImportacionLote,
    ImportacionObservacion, Puesto, Seccion, ServicioNivel1, ServicioNivel2,
    Sesion, TipoServicio, Usuario, utcnow,
)
from app.schemas import CatalogIn, LoginIn, OrgIn, OrgUpdate, ServiceN1In, ServiceN2In, ServiceN2Update, UserIn, UserUpdate
from app.security import COOKIE_NAME, create_session, csrf_for, get_current_user, hash_password, require_admin, token_hash, verify_password

app = FastAPI(title="Catálogo de Servicios", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

ORG = {
    "empresas": (Empresa, None, None),
    "areas": (Area, Empresa, "empresa_id"),
    "departamentos": (Departamento, Area, "area_id"),
    "secciones": (Seccion, Departamento, "departamento_id"),
    "puestos": (Puesto, Seccion, "seccion_id"),
}
CATALOGS = {"clases": ClaseServicio, "criticidades": Criticidad, "tipos": TipoServicio}

def fail_integrity(db: Session, exc: IntegrityError):
    db.rollback()
    message = str(exc.orig).lower()
    if "unique" in message or "duplicate" in message:
        raise HTTPException(409, "El código o nombre ya existe en el alcance indicado")
    if "foreign key" in message:
        raise HTTPException(409, "La referencia no existe o el registro tiene dependencias")
    raise HTTPException(400, "No fue posible guardar por una restricción de datos")

def row(item, parent_field=None):
    data = {"id": item.id, "codigo": item.codigo, "nombre": item.nombre, "activo": item.activo}
    if parent_field: data["parent_id"] = getattr(item, parent_field)
    return data

@app.get("/", include_in_schema=False)
def index(): return FileResponse("app/static/index.html")

@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}

@app.post("/api/auth/login")
def login(payload: LoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(Usuario).where(func.lower(Usuario.login) == payload.login.strip().lower()))
    if not user or not user.activo or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Credenciales inválidas o usuario inactivo")
    token = create_session(db, user)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", secure=os.getenv("APP_ENV") == "production", max_age=8 * 3600, path="/")
    return {"id": user.id, "nombre": user.nombre, "login": user.login, "rol": user.rol, "csrf": csrf_for(token)}

@app.post("/api/auth/logout")
def logout(request: Request, response: Response, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    token = request.state.session_token
    if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), csrf_for(token)):
        raise HTTPException(403, "Token CSRF inválido")
    session = db.scalar(select(Sesion).where(Sesion.token_hash == token_hash(token)))
    session.revocada_en = utcnow(); db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Sesión cerrada"}

@app.get("/api/me")
def me(request: Request, user: Usuario = Depends(get_current_user)):
    return {"id": user.id, "nombre": user.nombre, "login": user.login, "rol": user.rol, "csrf": csrf_for(request.state.session_token)}

@app.get("/api/organizacion/{kind}")
def list_org(kind: str, include_inactive: bool = False, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    if kind not in ORG: raise HTTPException(404, "Entidad no válida")
    model, _, parent_field = ORG[kind]
    stmt = select(model).order_by(model.codigo)
    if not include_inactive: stmt = stmt.where(model.activo.is_(True))
    return [row(x, parent_field) for x in db.scalars(stmt).all()]

@app.post("/api/organizacion/{kind}", status_code=201)
def create_org(kind: str, payload: OrgIn, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    if kind not in ORG: raise HTTPException(404, "Entidad no válida")
    model, parent_model, parent_field = ORG[kind]
    values = {"codigo": payload.codigo.strip(), "nombre": payload.nombre.strip()}
    if parent_model:
        if payload.parent_id is None: raise HTTPException(422, "El padre es obligatorio")
        parent = db.get(parent_model, payload.parent_id)
        if not parent or not parent.activo: raise HTTPException(422, "El padre no existe o está inactivo")
        values[parent_field] = parent.id
    item = model(**values); db.add(item)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return row(item, parent_field)

@app.patch("/api/organizacion/{kind}/{item_id}")
def update_org(kind: str, item_id: int, payload: OrgUpdate, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    if kind not in ORG: raise HTTPException(404, "Entidad no válida")
    model, parent_model, parent_field = ORG[kind]
    item = db.get(model, item_id)
    if not item: raise HTTPException(404, "Registro no encontrado")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("activo") is False:
        dependency = {Empresa: Area, Area: Departamento, Departamento: Seccion, Seccion: Puesto, Puesto: Usuario}.get(model)
        dependency_fk = {Empresa: "empresa_id", Area: "area_id", Departamento: "departamento_id", Seccion: "seccion_id", Puesto: "puesto_id"}.get(model)
        if dependency and db.scalar(select(dependency).where(getattr(dependency, dependency_fk) == item.id, dependency.activo.is_(True))):
            raise HTTPException(409, "No se puede desactivar: tiene dependencias activas")
        if model is Seccion and db.scalar(select(ServicioNivel2).where(ServicioNivel2.seccion_responsable_id == item.id, ServicioNivel2.activo.is_(True))):
            raise HTTPException(409, "No se puede desactivar: es responsable de servicios activos")
    if "parent_id" in changes:
        if not parent_model: changes.pop("parent_id")
        else:
            parent = db.get(parent_model, changes.pop("parent_id"))
            if not parent or not parent.activo: raise HTTPException(422, "El padre no existe o está inactivo")
            changes[parent_field] = parent.id
    for key, value in changes.items(): setattr(item, key, value.strip() if isinstance(value, str) else value)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return row(item, parent_field)

@app.get("/api/usuarios")
def users(include_inactive: bool = False, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = select(Usuario).order_by(Usuario.login)
    if not include_inactive: stmt = stmt.where(Usuario.activo.is_(True))
    return [{"id": x.id, "nombre": x.nombre, "login": x.login, "rol": x.rol, "activo": x.activo, "puesto_id": x.puesto_id} for x in db.scalars(stmt)]

def valid_position(db, position_id):
    if position_id is None: return
    position = db.get(Puesto, position_id)
    if not position or not position.activo: raise HTTPException(422, "El puesto no existe o está inactivo")

@app.post("/api/usuarios", status_code=201)
def create_user(payload: UserIn, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    valid_position(db, payload.puesto_id)
    item = Usuario(nombre=payload.nombre.strip(), login=payload.login.strip().lower(), password_hash=hash_password(payload.password), rol=payload.rol, puesto_id=payload.puesto_id)
    db.add(item)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return {"id": item.id, "nombre": item.nombre, "login": item.login, "rol": item.rol, "activo": item.activo, "puesto_id": item.puesto_id}

@app.patch("/api/usuarios/{item_id}")
def update_user(item_id: int, payload: UserUpdate, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(Usuario, item_id)
    if not item: raise HTTPException(404, "Usuario no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "puesto_id" in data: valid_position(db, data["puesto_id"])
    password = data.pop("password", None)
    if password: item.password_hash = hash_password(password)
    if "login" in data: data["login"] = data["login"].strip().lower()
    for key, value in data.items(): setattr(item, key, value)
    if data.get("activo") is False:
        for session in item.sesiones:
            if session.revocada_en is None: session.revocada_en = utcnow()
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return {"id": item.id, "nombre": item.nombre, "login": item.login, "rol": item.rol, "activo": item.activo, "puesto_id": item.puesto_id}

@app.get("/api/catalogos/{kind}")
def list_catalog(kind: str, include_inactive: bool = False, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    model = CATALOGS.get(kind)
    if not model: raise HTTPException(404, "Catálogo no válido")
    stmt = select(model).order_by(model.nombre)
    if not include_inactive: stmt = stmt.where(model.activo.is_(True))
    return [row(x) for x in db.scalars(stmt)]

@app.post("/api/catalogos/{kind}", status_code=201)
def create_catalog(kind: str, payload: CatalogIn, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    model = CATALOGS.get(kind)
    if not model: raise HTTPException(404, "Catálogo no válido")
    item = model(codigo=payload.codigo.strip(), nombre=payload.nombre.strip()); db.add(item)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return row(item)

@app.patch("/api/catalogos/{kind}/{item_id}")
def update_catalog(kind: str, item_id: int, payload: OrgUpdate, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    model = CATALOGS.get(kind)
    if not model: raise HTTPException(404, "Catálogo no válido")
    item = db.get(model, item_id)
    if not item: raise HTTPException(404, "Registro no encontrado")
    data = payload.model_dump(exclude_unset=True, include={"codigo", "nombre", "activo"})
    service_fk = {ClaseServicio: ServicioNivel2.clase_id, Criticidad: ServicioNivel2.criticidad_id, TipoServicio: ServicioNivel2.tipo_id}[model]
    if data.get("activo") is False and db.scalar(select(ServicioNivel2).where(service_fk == item.id, ServicioNivel2.activo.is_(True))):
        raise HTTPException(409, "No se puede desactivar: el catálogo está en uso por servicios activos")
    for key, value in data.items(): setattr(item, key, value)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return row(item)

@app.get("/api/servicios/nivel1")
def list_n1(include_inactive: bool = False, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(ServicioNivel1).order_by(ServicioNivel1.codigo)
    if not include_inactive: stmt = stmt.where(ServicioNivel1.activo.is_(True))
    return [row(x) for x in db.scalars(stmt)]

@app.post("/api/servicios/nivel1", status_code=201)
def create_n1(payload: ServiceN1In, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = ServicioNivel1(codigo=payload.codigo.strip(), nombre=payload.nombre.strip()); db.add(item)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return row(item)

@app.patch("/api/servicios/nivel1/{item_id}")
def update_n1(item_id: int, payload: OrgUpdate, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(ServicioNivel1, item_id)
    if not item: raise HTTPException(404, "Servicio nivel 1 no encontrado")
    data = payload.model_dump(exclude_unset=True, include={"codigo", "nombre", "activo"})
    if data.get("activo") is False and db.scalar(select(ServicioNivel2).where(ServicioNivel2.nivel1_id == item.id, ServicioNivel2.activo.is_(True))):
        raise HTTPException(409, "No se puede desactivar: tiene servicios nivel 2 activos")
    for key, value in data.items(): setattr(item, key, value)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return row(item)

def service_dict(x: ServicioNivel2):
    return {"id": x.id, "codigo": x.codigo, "codigo_original": x.codigo_original, "nombre": x.nombre,
        "nivel1_id": x.nivel1_id, "nivel1": x.nivel1.nombre, "indicador_activo_excel": x.indicador_activo_excel,
        "clase_id": x.clase_id, "clase": x.clase.nombre if x.clase else None,
        "criticidad_id": x.criticidad_id, "criticidad": x.criticidad.nombre if x.criticidad else None,
        "tipo_id": x.tipo_id, "tipo": x.tipo.nombre if x.tipo else None, "descripcion": x.descripcion,
        "metrica": x.metrica, "minimo": str(x.minimo) if x.minimo is not None else None,
        "maximo": str(x.maximo) if x.maximo is not None else None, "estado_revision": x.estado_revision,
        "seccion_responsable_id": x.seccion_responsable_id,
        "seccion_responsable": x.seccion_responsable.nombre if x.seccion_responsable else None,
        "usuario_responsable_id": x.usuario_responsable_id,
        "usuario_responsable": x.usuario_responsable.nombre if x.usuario_responsable else None,
        "origen_hoja": x.origen_hoja, "origen_fila": x.origen_fila, "origen_rango": x.origen_rango,
        "activo": x.activo}

@app.get("/api/servicios")
def list_services(q: str | None = None, nivel1_id: int | None = None, activo: bool | None = True,
    clase_id: int | None = None, criticidad_id: int | None = None, tipo_id: int | None = None,
    page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
    user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    filters = []
    if q: filters.append(or_(ServicioNivel2.codigo.ilike(f"%{q}%"), ServicioNivel2.nombre.ilike(f"%{q}%")))
    for col, value in [(ServicioNivel2.nivel1_id,nivel1_id),(ServicioNivel2.activo,activo),(ServicioNivel2.clase_id,clase_id),(ServicioNivel2.criticidad_id,criticidad_id),(ServicioNivel2.tipo_id,tipo_id)]:
        if value is not None: filters.append(col == value)
    total = db.scalar(select(func.count()).select_from(ServicioNivel2).where(*filters)) or 0
    stmt = select(ServicioNivel2).options(
        joinedload(ServicioNivel2.nivel1), joinedload(ServicioNivel2.clase),
        joinedload(ServicioNivel2.criticidad), joinedload(ServicioNivel2.tipo),
        joinedload(ServicioNivel2.seccion_responsable), joinedload(ServicioNivel2.usuario_responsable),
    ).where(*filters).order_by(ServicioNivel2.codigo).offset((page-1)*size).limit(size)
    return {"items": [service_dict(x) for x in db.scalars(stmt)], "page": page, "size": size, "total": total, "pages": (total + size - 1)//size}

@app.get("/api/servicios/{item_id}")
def get_service(item_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.get(ServicioNivel2, item_id)
    if not item: raise HTTPException(404, "Servicio no encontrado")
    return service_dict(item)

def validate_service_refs(db: Session, data: dict[str, Any], current: ServicioNivel2 | None = None):
    merged = {key: getattr(current, key) for key in ["nivel1_id","clase_id","criticidad_id","tipo_id","minimo","maximo","seccion_responsable_id","usuario_responsable_id"]} if current else {}
    merged.update(data)
    n1 = db.get(ServicioNivel1, merged.get("nivel1_id"))
    if not n1 or not n1.activo: raise HTTPException(422, "El servicio nivel 1 no existe o está inactivo")
    for key, model in [("clase_id",ClaseServicio),("criticidad_id",Criticidad),("tipo_id",TipoServicio),("seccion_responsable_id",Seccion)]:
        value = merged.get(key)
        if value is not None:
            target = db.get(model, value)
            if not target or not target.activo: raise HTTPException(422, f"Referencia {key} inexistente o inactiva")
    minimum, maximum = merged.get("minimo"), merged.get("maximo")
    if minimum is not None and maximum is not None and minimum > maximum: raise HTTPException(422, "mínimo no puede ser mayor que máximo")
    uid, sid = merged.get("usuario_responsable_id"), merged.get("seccion_responsable_id")
    if uid:
        responsible = db.get(Usuario, uid)
        if not responsible or not responsible.activo or not responsible.puesto or responsible.puesto.seccion_id != sid:
            raise HTTPException(422, "El usuario responsable debe estar activo y pertenecer a la sección responsable")

@app.post("/api/servicios", status_code=201)
def create_service(payload: ServiceN2In, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    data = payload.model_dump(); validate_service_refs(db, data)
    item = ServicioNivel2(**data); db.add(item)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return service_dict(item)

@app.patch("/api/servicios/{item_id}")
def update_service(item_id: int, payload: ServiceN2Update, admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(ServicioNivel2, item_id)
    if not item: raise HTTPException(404, "Servicio no encontrado")
    data = payload.model_dump(exclude_unset=True); validate_service_refs(db, data, item)
    for key, value in data.items(): setattr(item, key, value)
    try: db.commit(); db.refresh(item)
    except IntegrityError as exc: fail_integrity(db, exc)
    return service_dict(item)

@app.post("/api/importaciones")
def run_import(admin: Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    path = Path("data/CatalogoServicios.xlsx")
    if not path.is_file(): raise HTTPException(424, "Falta data/CatalogoServicios.xlsx; agregue el original sin modificar")
    try:
        result = import_excel(db, path)
        from app.cli import ensure_demo
        ensure_demo(db, assign_services=True); db.commit()
        return result.dict()
    except ValueError as exc: raise HTTPException(422, str(exc))

@app.get("/api/importaciones")
def imports(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    lots = db.scalars(select(ImportacionLote).order_by(ImportacionLote.id.desc())).all()
    return [{"id": x.id, "archivo": x.archivo, "sha256": x.sha256, "estado": x.estado, "creados": x.creados,
             "actualizados": x.actualizados, "omitidos": x.omitidos, "observados": x.observados,
             "iniciada_en": x.iniciada_en, "finalizada_en": x.finalizada_en} for x in lots]

@app.get("/api/importaciones/{lote_id}/observaciones")
def observations(lote_id: int, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(ImportacionObservacion).where(ImportacionObservacion.lote_id == lote_id).order_by(ImportacionObservacion.id)).all()
    return [{"hoja": x.hoja, "fila": x.fila, "rango_origen": x.rango_origen, "codigo": x.codigo,
             "tipo": x.tipo, "detalle": x.detalle, "valor_original": x.valor_original, "valor_canonico": x.valor_canonico} for x in rows]

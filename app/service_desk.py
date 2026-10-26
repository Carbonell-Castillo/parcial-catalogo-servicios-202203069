"""API del Service Desk y CMDB.

Las reglas se concentran aquí para que las transiciones, autorización y auditoría
sean idénticas para la interfaz y cualquier cliente de API.
"""
from __future__ import annotations

import hmac
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (ArticuloConocimiento, ClasificacionCI, Cola, ColaMiembro, ColaRol,
    DispositivoCI, Notificacion, RelacionCI, ServicioCI, ServicioNivel2, Ticket,
    TicketAdjunto, TicketCI, TicketComentario, TicketHistorial, TicketRelacion,
    Usuario, UsuarioRol, utcnow)
from app.security import csrf_for, get_current_user

router = APIRouter(prefix="/api")

PROCESOS = {
    "nuevos_servicios": ["solicitud", "analisis", "aprobado", "implementacion", "resuelto", "cerrado"],
    "cambios": ["solicitud", "evaluacion", "aprobado", "planificacion", "ejecucion", "validacion", "resuelto", "cerrado"],
    "incidentes": ["registro", "clasificacion", "diagnostico", "atencion", "escalado", "recuperacion", "resuelto", "cerrado"],
    "eventos": ["registro", "clasificacion", "evaluacion", "respuesta", "resuelto", "cerrado"],
    "problemas": ["registro", "investigacion", "causa_raiz", "error_conocido", "solucion_definitiva", "resuelto", "cerrado"],
    "accesos": ["solicitud", "aprobado", "provision", "validacion", "resuelto", "cerrado"],
    "servicios_tecnologia": ["solicitud", "validacion", "asignacion", "cumplimiento", "confirmacion", "resuelto", "cerrado"],
}
TIPOS = {
    "nuevos_servicios": "requisicion_servicio", "cambios": "solicitud_cambio",
    "incidentes": "incidente", "eventos": "evento", "problemas": "problema",
    "accesos": "solicitud_acceso", "servicios_tecnologia": "requisicion_servicio",
}
PRIORIDAD_ORDEN = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
RELACIONES_ACICLICAS = {"depende_de", "alojado_en", "padre_de"}
MIMES = {"application/pdf", "image/png", "image/jpeg", "text/plain"}
MAX_FILE = 5 * 1024 * 1024


class ColaIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=40)
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str | None = None
    proceso: str
    nivel_soporte: int = Field(ge=0, le=4, default=1)
    regla_orden: str = "prioridad_antiguedad"
    objetivo_primera_min: int = Field(gt=0, default=240)
    objetivo_resolucion_min: int = Field(gt=0, default=1440)
    calendario: str = "calendario"


class MiembroIn(BaseModel):
    usuario_id: int
    puede_consultar: bool = True
    puede_atender: bool = False
    puede_transferir: bool = False
    puede_aprobar: bool = False
    puede_administrar: bool = False


class TicketIn(BaseModel):
    titulo: str = Field(min_length=3, max_length=240)
    descripcion: str = Field(min_length=3)
    solicitante_id: int | None = None
    servicio_id: int
    proceso: str
    cola_id: int
    tipo: str | None = None
    prioridad: str = "media"
    impacto: str = "medio"
    urgencia: str = "media"
    canal: str = "portal"
    ci_ids: list[int] = []
    sin_ci_justificacion: str | None = None
    datos_proceso: dict[str, Any] = {}


class TransicionIn(BaseModel):
    estado: str
    motivo: str | None = None
    datos: dict[str, Any] = {}


class TransferIn(BaseModel):
    cola_id: int
    motivo: str = Field(min_length=3)


class ComentarioIn(BaseModel):
    texto: str = Field(min_length=1)
    interno: bool = False


class ClasificacionIn(BaseModel):
    codigo: str = Field(min_length=1, max_length=60)
    nombre: str = Field(min_length=1, max_length=160)
    padre_id: int | None = None
    atributos_definidos: dict[str, Any] = {}
    origen: str = "Decisión del proyecto"


class DispositivoIn(BaseModel):
    etiqueta: str = Field(min_length=1, max_length=80)
    nombre: str = Field(min_length=1, max_length=180)
    clasificacion_id: int
    estado: str = "Activo"
    ubicacion: str
    responsable_id: int | None = None
    numero_serie: str | None = None
    version: str | None = None
    nivel_seguridad: str | None = None
    cumplimiento: str | None = None
    estado_configuracion: str | None = None
    licencia: str | None = None
    atributos: dict[str, Any] = {}


class RelacionCIIn(BaseModel):
    origen_id: int
    destino_id: int
    tipo: str
    permite_ciclo: bool = False


class RolColaIn(BaseModel):
    rol: str
    puede_consultar: bool = True
    puede_atender: bool = False
    puede_transferir: bool = False
    puede_aprobar: bool = False
    puede_administrar: bool = False


def mutation_user(request: Request, user: Usuario = Depends(get_current_user)) -> Usuario:
    if not hmac.compare_digest(request.headers.get("X-CSRF-Token", ""), csrf_for(request.state.session_token)):
        raise HTTPException(403, "Token CSRF inválido")
    return user


def admin(user: Usuario):
    if user.rol != "administrador":
        raise HTTPException(403, "Se requiere rol administrador")


def roles(db: Session, user: Usuario) -> set[str]:
    return set(db.scalars(select(UsuarioRol.rol).where(UsuarioRol.usuario_id == user.id)))


def permission(db: Session, user: Usuario, cola_id: int, name: str) -> bool:
    if user.rol == "administrador": return True
    attr = getattr(ColaMiembro, f"puede_{name}")
    if db.scalar(select(ColaMiembro.id).where(ColaMiembro.cola_id == cola_id, ColaMiembro.usuario_id == user.id, attr.is_(True))):
        return True
    rs = roles(db, user)
    if not rs: return False
    rattr = getattr(ColaRol, f"puede_{name}")
    return db.scalar(select(ColaRol.id).where(ColaRol.cola_id == cola_id, ColaRol.rol.in_(rs), rattr.is_(True))) is not None


def can_see(db: Session, user: Usuario, ticket: Ticket, internal: bool = False):
    if user.rol == "administrador" or permission(db, user, ticket.cola_id, "consultar"): return
    if ticket.solicitante_id == user.id and not internal: return
    raise HTTPException(403, "Ticket fuera de su alcance")


def audit(db: Session, ticket: Ticket, actor: Usuario, action: str, old=None, new=None, reason=None):
    db.add(TicketHistorial(ticket_id=ticket.id, actor_id=actor.id, accion=action,
        anterior=old, nuevo=new, motivo=reason))


def ticket_dict(db: Session, t: Ticket, detail=False):
    d = {"id": t.id, "numero": t.numero, "titulo": t.titulo, "descripcion": t.descripcion,
        "solicitante_id": t.solicitante_id, "creador_id": t.creador_id,
        "servicio_id": t.servicio_id, "servicio": t.servicio.nombre, "nivel1_id": t.servicio.nivel1_id,
        "tipo": t.tipo, "proceso": t.proceso, "cola_id": t.cola_id, "cola": t.cola.nombre,
        "responsable_id": t.responsable_id, "estado": t.estado, "prioridad": t.prioridad,
        "impacto": t.impacto, "urgencia": t.urgencia, "canal": t.canal,
        "sin_ci_justificacion": t.sin_ci_justificacion, "datos_proceso": t.datos_proceso,
        "creado_en": t.creado_en, "actualizado_en": t.actualizado_en,
        "primera_atencion_en": t.primera_atencion_en, "resuelto_en": t.resuelto_en,
        "cerrado_en": t.cerrado_en, "reaperturas": t.reaperturas}
    if detail:
        d["ci_ids"] = list(db.scalars(select(TicketCI.ci_id).where(TicketCI.ticket_id == t.id)))
        d["historial"] = [{"accion": h.accion, "actor_id": h.actor_id, "anterior": h.anterior,
            "nuevo": h.nuevo, "motivo": h.motivo, "creado_en": h.creado_en} for h in db.scalars(
            select(TicketHistorial).where(TicketHistorial.ticket_id == t.id).order_by(TicketHistorial.id))]
        d["relaciones"] = [{"id":r.id,"ticket_id":r.ticket_id,"relacionado_id":r.relacionado_id,"tipo":r.tipo} for r in db.scalars(select(TicketRelacion).where(or_(TicketRelacion.ticket_id==t.id,TicketRelacion.relacionado_id==t.id)).order_by(TicketRelacion.id))]
    return d


@router.get("/service-desk/configuracion")
def configuration(user: Usuario = Depends(get_current_user)):
    return {"procesos": PROCESOS, "tipos_por_proceso": TIPOS,
        "incidentes": {"I0": "sin interrupción", "I1": "<=3 horas", "I2": "<=8 horas", "I3": "<=2 días", "I4": "<=1 semana", "I5": ">=1 mes", "I6": "seguridad"},
        "eventos": {"E0": "programado", "E1": "sin impacto", "E2": "impacto al servicio", "E3": "seguridad"},
        "niveles_soporte": {"0": "Autoservicio", "1": "Help Desk", "2": "Soporte Técnico", "3": "Ingenieros/proveedores", "4": "Externo configurable"},
        "objetivos": "minutos calendario; las pausas se informan por separado y no se descuentan"}


@router.get("/colas")
def queues(include_inactive: bool = False, user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Cola).order_by(Cola.proceso, Cola.codigo)
    if not include_inactive: q = q.where(Cola.activo.is_(True))
    return [{"id": x.id, "codigo": x.codigo, "nombre": x.nombre, "descripcion": x.descripcion,
        "proceso": x.proceso, "nivel_soporte": x.nivel_soporte, "regla_orden": x.regla_orden,
        "objetivo_primera_min": x.objetivo_primera_min, "objetivo_resolucion_min": x.objetivo_resolucion_min,
        "calendario": x.calendario, "activo": x.activo} for x in db.scalars(q)]


@router.post("/colas", status_code=201)
def create_queue(p: ColaIn, user: Usuario = Depends(mutation_user), db: Session = Depends(get_db)):
    admin(user)
    if p.proceso not in PROCESOS: raise HTTPException(422, "Proceso no válido")
    x = Cola(**p.model_dump()); db.add(x)
    try: db.commit(); db.refresh(x)
    except IntegrityError: db.rollback(); raise HTTPException(409, "Código de cola duplicado")
    return {"id": x.id, **p.model_dump(), "activo": x.activo}


@router.patch("/colas/{queue_id}")
def update_queue(queue_id: int, data: dict[str, Any], user: Usuario = Depends(mutation_user), db: Session = Depends(get_db)):
    admin(user); x = db.get(Cola, queue_id)
    if not x: raise HTTPException(404, "Cola no encontrada")
    if data.get("proceso") and data["proceso"] not in PROCESOS: raise HTTPException(422, "Proceso no válido")
    if data.get("activo") is False and db.scalar(select(Ticket.id).where(Ticket.cola_id == x.id, Ticket.activo.is_(True), Ticket.estado != "cerrado")):
        raise HTTPException(409, "La cola tiene tickets activos; transfiéralos antes")
    for k in {"nombre","descripcion","proceso","nivel_soporte","regla_orden","objetivo_primera_min","objetivo_resolucion_min","calendario","activo"} & data.keys(): setattr(x, k, data[k])
    db.commit(); return {"id": x.id, "activo": x.activo}


@router.post("/colas/{queue_id}/miembros")
def set_member(queue_id: int, p: MiembroIn, user: Usuario = Depends(mutation_user), db: Session = Depends(get_db)):
    admin(user)
    if not db.get(Cola, queue_id) or not db.get(Usuario, p.usuario_id): raise HTTPException(422, "Cola o usuario inexistente")
    x = db.scalar(select(ColaMiembro).where(ColaMiembro.cola_id == queue_id, ColaMiembro.usuario_id == p.usuario_id))
    if not x: x = ColaMiembro(cola_id=queue_id, **p.model_dump()); db.add(x)
    else:
        for k,v in p.model_dump(exclude={"usuario_id"}).items(): setattr(x,k,v)
    db.commit(); return {"id": x.id, "cola_id": queue_id, **p.model_dump()}


@router.post("/colas/{queue_id}/roles")
def set_queue_role(queue_id:int,p:RolColaIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user)
    if not db.get(Cola,queue_id):raise HTTPException(422,"Cola inexistente")
    x=db.scalar(select(ColaRol).where(ColaRol.cola_id==queue_id,ColaRol.rol==p.rol))
    if not x:x=ColaRol(cola_id=queue_id,**p.model_dump());db.add(x)
    else:
        for k,v in p.model_dump(exclude={"rol"}).items():setattr(x,k,v)
    db.commit();return {"id":x.id,"cola_id":queue_id,**p.model_dump()}


@router.post("/usuarios/{user_id}/roles/{role}",status_code=201)
def grant_role(user_id:int,role:str,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user)
    if role not in {"solicitante","agente","aprobador"}:raise HTTPException(422,"Rol operativo no válido")
    if not db.get(Usuario,user_id):raise HTTPException(404,"Usuario no encontrado")
    x=db.scalar(select(UsuarioRol).where(UsuarioRol.usuario_id==user_id,UsuarioRol.rol==role))
    if not x:x=UsuarioRol(usuario_id=user_id,rol=role);db.add(x);db.commit();db.refresh(x)
    return {"id":x.id,"usuario_id":user_id,"rol":role}


@router.post("/tickets", status_code=201)
def create_ticket(p: TicketIn, user: Usuario = Depends(mutation_user), db: Session = Depends(get_db)):
    if p.proceso not in PROCESOS: raise HTTPException(422, "Proceso no válido")
    queue = db.get(Cola, p.cola_id); service = db.get(ServicioNivel2, p.servicio_id)
    if not queue or not queue.activo or queue.proceso != p.proceso: raise HTTPException(422, "La cola activa debe corresponder al proceso")
    if not service or not service.activo: raise HTTPException(422, "Servicio inexistente o inactivo")
    requester = p.solicitante_id or user.id
    if not db.get(Usuario, requester): raise HTTPException(422, "Solicitante inexistente")
    if not p.ci_ids and not (p.sin_ci_justificacion or "").strip(): raise HTTPException(422, "Asocie CI o justifique por qué no aplica")
    for ci in set(p.ci_ids):
        if not db.get(DispositivoCI, ci): raise HTTPException(422, f"CI {ci} inexistente")
    if p.tipo and p.tipo != TIPOS[p.proceso]: raise HTTPException(422, "Tipo incompatible con el proceso")
    if p.proceso == "incidentes": validate_incident(p.datos_proceso)
    if p.proceso == "eventos" and p.datos_proceso.get("categoria") not in {"E0","E1","E2","E3"}: raise HTTPException(422, "Categoría de evento E0-E3 obligatoria")
    t = Ticket(numero="PENDIENTE", titulo=p.titulo.strip(), descripcion=p.descripcion.strip(),
        solicitante_id=requester, creador_id=user.id, servicio_id=p.servicio_id,
        tipo=p.tipo or TIPOS[p.proceso], proceso=p.proceso, cola_id=p.cola_id,
        estado=PROCESOS[p.proceso][0], prioridad=p.prioridad, impacto=p.impacto,
        urgencia=p.urgencia, canal=p.canal, sin_ci_justificacion=p.sin_ci_justificacion,
        datos_proceso=p.datos_proceso)
    db.add(t); db.flush(); t.numero = f"SD-{t.id:07d}"
    for ci in set(p.ci_ids): db.add(TicketCI(ticket_id=t.id, ci_id=ci))
    audit(db, t, user, "creacion", None, {"estado": t.estado, "cola_id": t.cola_id})
    db.commit(); db.refresh(t); return ticket_dict(db, t, True)


def ticket_filters(stmt, numero, servicio_id, proceso, cola_id, estado, prioridad, responsable_id, desde, hasta):
    vals = [(Ticket.servicio_id,servicio_id),(Ticket.proceso,proceso),(Ticket.cola_id,cola_id),(Ticket.estado,estado),(Ticket.prioridad,prioridad),(Ticket.responsable_id,responsable_id)]
    for col,val in vals:
        if val is not None: stmt=stmt.where(col==val)
    if numero: stmt=stmt.where(Ticket.numero.ilike(f"%{numero}%"))
    if desde: stmt=stmt.where(Ticket.creado_en >= desde)
    if hasta: stmt=stmt.where(Ticket.creado_en <= hasta)
    return stmt


@router.get("/tickets")
def list_tickets(numero: str|None=None, servicio_id:int|None=None, proceso:str|None=None, cola_id:int|None=None,
    estado:str|None=None, prioridad:str|None=None, responsable_id:int|None=None, desde:datetime|None=None, hasta:datetime|None=None,
    page:int=Query(1,ge=1), size:int=Query(20,ge=1,le=100), user:Usuario=Depends(get_current_user), db:Session=Depends(get_db)):
    stmt=select(Ticket)
    if user.rol != "administrador":
        allowed=list(db.scalars(select(ColaMiembro.cola_id).where(ColaMiembro.usuario_id==user.id, ColaMiembro.puede_consultar.is_(True))))
        rs=roles(db,user)
        if rs: allowed += list(db.scalars(select(ColaRol.cola_id).where(ColaRol.rol.in_(rs), ColaRol.puede_consultar.is_(True))))
        stmt=stmt.where(or_(Ticket.solicitante_id==user.id, Ticket.cola_id.in_(set(allowed))))
    stmt=ticket_filters(stmt,numero,servicio_id,proceso,cola_id,estado,prioridad,responsable_id,desde,hasta)
    total=db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order=case(PRIORIDAD_ORDEN, value=Ticket.prioridad, else_=9)
    rows=db.scalars(stmt.order_by(order,Ticket.creado_en,Ticket.id).offset((page-1)*size).limit(size)).all()
    return {"items":[ticket_dict(db,x) for x in rows],"page":page,"size":size,"total":total,"pages":max(1,(total+size-1)//size)}


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id:int,user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: raise HTTPException(404,"Ticket no encontrado")
    can_see(db,user,t); d=ticket_dict(db,t,True)
    d["comentarios"]=[{"id":c.id,"autor_id":c.autor_id,"texto":c.texto,"interno":c.interno,"creado_en":c.creado_en} for c in db.scalars(select(TicketComentario).where(TicketComentario.ticket_id==t.id, or_(TicketComentario.interno.is_(False), TicketComentario.autor_id==user.id) if t.solicitante_id==user.id and user.rol!="administrador" else True).order_by(TicketComentario.id))]
    d["adjuntos"]=[{"id":a.id,"nombre":a.nombre,"tipo_mime":a.tipo_mime,"tamano":a.tamano} for a in db.scalars(select(TicketAdjunto).where(TicketAdjunto.ticket_id==t.id))]
    return d


@router.post("/tickets/{ticket_id}/tomar")
def claim(ticket_id:int,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: raise HTTPException(404,"Ticket no encontrado")
    if not permission(db,user,t.cola_id,"atender"): raise HTTPException(403,"No puede atender esta cola")
    result=db.execute(update(Ticket).where(Ticket.id==ticket_id,Ticket.responsable_id.is_(None)).values(responsable_id=user.id,primera_atencion_en=func.coalesce(Ticket.primera_atencion_en,utcnow())))
    if result.rowcount != 1: db.rollback(); raise HTTPException(409,"El ticket ya fue tomado por otro agente")
    audit(db,t,user,"asignacion",{"responsable_id":None},{"responsable_id":user.id}); db.commit()
    return {"responsable_id":user.id}


@router.post("/tickets/{ticket_id}/transferir")
def transfer(ticket_id:int,p:TransferIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: raise HTTPException(404,"Ticket no encontrado")
    if not permission(db,user,t.cola_id,"transferir"): raise HTTPException(403,"No puede transferir este ticket")
    target=db.get(Cola,p.cola_id)
    if not target or not target.activo or target.proceso != t.proceso: raise HTTPException(422,"La cola destino debe estar activa y ser del mismo proceso")
    old={"cola_id":t.cola_id,"responsable_id":t.responsable_id}; t.cola_id=target.id; t.responsable_id=None
    audit(db,t,user,"transferencia",old,{"cola_id":target.id,"responsable_id":None},p.motivo); db.commit()
    return {"cola_id":target.id}


def transition_allowed(t:Ticket,target:str)->bool:
    flow=PROCESOS[t.proceso]
    if t.estado=="cerrado" and target=="reabierto": return True
    if t.estado=="reabierto" and target in flow[1:-1]: return True
    if target=="rechazado" and t.proceso in {"nuevos_servicios","cambios","accesos"} and t.estado in {"analisis","evaluacion","solicitud"}: return True
    try: return flow.index(target)==flow.index(t.estado)+1
    except ValueError: return False


@router.post("/tickets/{ticket_id}/transiciones")
def transition(ticket_id:int,p:TransicionIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: raise HTTPException(404,"Ticket no encontrado")
    if not permission(db,user,t.cola_id,"atender"): raise HTTPException(403,"No puede atender este ticket")
    if not transition_allowed(t,p.estado): raise HTTPException(409,f"Transición {t.estado} → {p.estado} no permitida")
    if p.estado in {"aprobado","rechazado"}:
        if not permission(db,user,t.cola_id,"aprobar"): raise HTTPException(403,"No tiene permiso de aprobación")
        if t.proceso=="accesos" and t.solicitante_id==user.id: raise HTTPException(409,"El solicitante no puede autoaprobar su acceso")
    if t.proceso=="cambios" and p.estado=="ejecucion" and t.estado!="planificacion": raise HTTPException(409,"No puede ejecutar un cambio sin aprobación y planificación")
    merged={**(t.datos_proceso or {}),**p.datos}
    validate_process_exit(t,p.estado,merged)
    old=t.estado; t.estado=p.estado; t.datos_proceso=merged
    if t.primera_atencion_en is None: t.primera_atencion_en=utcnow()
    if p.estado=="resuelto": t.resuelto_en=utcnow()
    if p.estado=="cerrado":
        if not t.resuelto_en: raise HTTPException(409,"No se puede cerrar sin resolución")
        t.cerrado_en=utcnow()
    if p.estado=="reabierto": t.reaperturas+=1; t.cerrado_en=None; t.resuelto_en=None
    audit(db,t,user,"transicion",{"estado":old},{"estado":p.estado,"datos":p.datos},p.motivo)
    if t.proceso=="eventos" and p.estado in {"respuesta","resuelto"} and merged.get("categoria") in {"E2","E3"}: ensure_event_incident(db,t,user)
    db.commit(); return ticket_dict(db,t,True)


@router.post("/tickets/{ticket_id}/relaciones",status_code=201)
def relate_ticket(ticket_id:int,data:dict,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id);other=db.get(Ticket,data.get("relacionado_id"))
    if not t or not other or t.id==other.id:raise HTTPException(422,"Tickets inválidos")
    can_see(db,user,t);can_see(db,user,other)
    kind=str(data.get("tipo") or "relacionado")[:40]
    x=TicketRelacion(ticket_id=t.id,relacionado_id=other.id,tipo=kind);db.add(x)
    try:db.commit();db.refresh(x)
    except IntegrityError:db.rollback();raise HTTPException(409,"Relación duplicada")
    return {"id":x.id}


def validate_process_exit(t:Ticket,target:str,d:dict):
    required={
        ("nuevos_servicios","analisis"):["necesidad","viabilidad"],
        ("cambios","evaluacion"):["impacto","riesgo","plan_pruebas","plan_reversion"],
        ("incidentes","clasificacion"):["categoria","interrupcion","redundancia"],
        ("problemas","causa_raiz"):["causa_raiz"],
        ("accesos","aprobado"):["beneficiario_id","recurso","permiso"],
        ("servicios_tecnologia","cumplimiento"):["resultado_cumplimiento"],
    }.get((t.proceso,target),[])
    missing=[x for x in required if d.get(x) in (None,"")]
    if missing: raise HTTPException(422,"Evidencia requerida: "+", ".join(missing))
    if t.proceso=="incidentes": validate_incident(d)


def validate_incident(d:dict):
    cat=d.get("categoria")
    if cat not in {f"I{i}" for i in range(7)}: raise HTTPException(422,"Categoría I0-I6 obligatoria")
    if cat=="I6" and not d.get("seguridad"): raise HTTPException(422,"I6 debe registrar impacto de seguridad")
    # Regla complementaria del proyecto: los huecos/solapes temporales no se
    # clasifican automáticamente; el agente elige I0-I5 y deja justificación.
    if d.get("duracion_estimada_min") is not None and not d.get("justificacion_categoria"):
        raise HTTPException(422,"La duración requiere justificación manual de la categoría")


def ensure_event_incident(db:Session,event:Ticket,user:Usuario):
    existing=db.scalar(select(TicketRelacion.relacionado_id).where(TicketRelacion.ticket_id==event.id,TicketRelacion.tipo=="genera_incidente"))
    if existing: return existing
    queue=db.scalar(select(Cola).where(Cola.proceso=="incidentes",Cola.activo.is_(True)).order_by(Cola.id))
    if not queue: raise HTTPException(409,"No existe cola activa de incidentes")
    d=event.datos_proceso or {}; inc=Ticket(numero="PENDIENTE",titulo=f"Incidente por {event.numero}",descripcion=event.descripcion,
        solicitante_id=event.solicitante_id,creador_id=user.id,servicio_id=event.servicio_id,tipo="incidente",proceso="incidentes",
        cola_id=queue.id,estado="registro",prioridad=event.prioridad,impacto=event.impacto,urgencia=event.urgencia,canal="evento",
        sin_ci_justificacion=event.sin_ci_justificacion,datos_proceso={"categoria":"I6" if d.get("categoria")=="E3" else "I1","interrupcion":True,"redundancia":"por_evaluar","justificacion_categoria":"Creado desde evento"})
    db.add(inc);db.flush();inc.numero=f"SD-{inc.id:07d}"
    for ci in db.scalars(select(TicketCI.ci_id).where(TicketCI.ticket_id==event.id)): db.add(TicketCI(ticket_id=inc.id,ci_id=ci))
    db.add(TicketRelacion(ticket_id=event.id,relacionado_id=inc.id,tipo="genera_incidente"))
    db.add(Notificacion(ticket_id=event.id,destinatario_id=event.solicitante_id,mensaje=f"{event.numero} generó {inc.numero}"))
    audit(db,inc,user,"creacion_desde_evento",None,{"evento_id":event.id})
    audit(db,event,user,"incidente_generado",None,{"incidente_id":inc.id})
    return inc.id


@router.post("/tickets/{ticket_id}/comentarios",status_code=201)
def comment(ticket_id:int,p:ComentarioIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: raise HTTPException(404,"Ticket no encontrado")
    can_see(db,user,t,p.interno)
    if p.interno and not permission(db,user,t.cola_id,"atender"): raise HTTPException(403,"Solo agentes pueden crear notas internas")
    x=TicketComentario(ticket_id=t.id,autor_id=user.id,**p.model_dump());db.add(x);audit(db,t,user,"nota_interna" if p.interno else "comentario");db.commit();return {"id":x.id}


@router.post("/tickets/{ticket_id}/adjuntos",status_code=201)
async def upload(ticket_id:int,archivo:UploadFile=File(...),user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    t=db.get(Ticket,ticket_id)
    if not t: raise HTTPException(404,"Ticket no encontrado")
    can_see(db,user,t); content=await archivo.read(MAX_FILE+1)
    if len(content)>MAX_FILE: raise HTTPException(413,"Adjunto supera 5 MiB")
    if archivo.content_type not in MIMES: raise HTTPException(415,"Tipo de archivo no permitido")
    x=TicketAdjunto(ticket_id=t.id,autor_id=user.id,nombre=(archivo.filename or "archivo")[:240],tipo_mime=archivo.content_type,tamano=len(content),contenido=content);db.add(x);audit(db,t,user,"adjunto",new={"nombre":x.nombre,"tamano":x.tamano});db.commit();return {"id":x.id,"nombre":x.nombre}


@router.get("/adjuntos/{attachment_id}")
def download(attachment_id:int,user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    x=db.get(TicketAdjunto,attachment_id)
    if not x: raise HTTPException(404,"Adjunto no encontrado")
    t=db.get(Ticket,x.ticket_id);can_see(db,user,t)
    safe=x.nombre.replace('"','')
    return Response(x.contenido,media_type=x.tipo_mime,headers={"Content-Disposition":f'attachment; filename="{safe}"',"X-Content-Type-Options":"nosniff"})


@router.get("/cmdb/clasificaciones")
def classifications(user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    return [{"id":x.id,"codigo":x.codigo,"nombre":x.nombre,"padre_id":x.padre_id,"atributos_definidos":x.atributos_definidos,"origen":x.origen,"activo":x.activo} for x in db.scalars(select(ClasificacionCI).order_by(ClasificacionCI.id))]


def class_has_ancestor(db:Session,start:int|None,target:int)->bool:
    seen=set()
    while start:
        if start==target:return True
        if start in seen:return True
        seen.add(start);x=db.get(ClasificacionCI,start);start=x.padre_id if x else None
    return False


@router.post("/cmdb/clasificaciones",status_code=201)
def create_class(p:ClasificacionIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user)
    if p.padre_id and not db.get(ClasificacionCI,p.padre_id):raise HTTPException(422,"Padre inexistente")
    x=ClasificacionCI(**p.model_dump());db.add(x)
    try:db.commit();db.refresh(x)
    except IntegrityError:db.rollback();raise HTTPException(409,"Código duplicado dentro del padre")
    return {"id":x.id}


@router.patch("/cmdb/clasificaciones/{class_id}")
def update_class(class_id:int,data:dict,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user);x=db.get(ClasificacionCI,class_id)
    if not x:raise HTTPException(404,"Clasificación no encontrada")
    parent=data.get("padre_id",x.padre_id)
    if parent==x.id or class_has_ancestor(db,parent,x.id):raise HTTPException(409,"La jerarquía no admite ciclos")
    if parent and not db.get(ClasificacionCI,parent):raise HTTPException(422,"Padre inexistente")
    for k in {"codigo","nombre","padre_id","atributos_definidos","origen","activo"}&data.keys():setattr(x,k,data[k])
    db.commit();return {"id":x.id}


def device_dict(x:DispositivoCI):
    return {"id":x.id,"etiqueta":x.etiqueta,"nombre":x.nombre,"clasificacion_id":x.clasificacion_id,"clasificacion":x.clasificacion.nombre,"estado":x.estado,"ubicacion":x.ubicacion,"responsable_id":x.responsable_id,"numero_serie":x.numero_serie,"version":x.version,"nivel_seguridad":x.nivel_seguridad,"cumplimiento":x.cumplimiento,"estado_configuracion":x.estado_configuracion,"licencia":x.licencia,"atributos":x.atributos,"activo":x.activo}


@router.get("/cmdb/dispositivos")
def devices(q:str|None=None,clasificacion_id:int|None=None,estado:str|None=None,ubicacion:str|None=None,page:int=Query(1,ge=1),size:int=Query(50,ge=1,le=200),user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=select(DispositivoCI)
    if q:stmt=stmt.where(or_(DispositivoCI.etiqueta.ilike(f"%{q}%"),DispositivoCI.nombre.ilike(f"%{q}%"),DispositivoCI.numero_serie.ilike(f"%{q}%")))
    for col,val in [(DispositivoCI.clasificacion_id,clasificacion_id),(DispositivoCI.estado,estado),(DispositivoCI.ubicacion,ubicacion)]:
        if val is not None:stmt=stmt.where(col==val)
    total=db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows=db.scalars(stmt.order_by(DispositivoCI.etiqueta).offset((page-1)*size).limit(size)).all()
    return {"items":[device_dict(x) for x in rows],"page":page,"size":size,"total":total,"pages":max(1,(total+size-1)//size)}


@router.post("/cmdb/dispositivos",status_code=201)
def create_device(p:DispositivoIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user)
    if not db.get(ClasificacionCI,p.clasificacion_id):raise HTTPException(422,"Clasificación inexistente")
    if p.responsable_id and not db.get(Usuario,p.responsable_id):raise HTTPException(422,"Responsable inexistente")
    x=DispositivoCI(**p.model_dump());db.add(x)
    try:db.commit();db.refresh(x)
    except IntegrityError:db.rollback();raise HTTPException(409,"Etiqueta o serie duplicada")
    return device_dict(x)


@router.patch("/cmdb/dispositivos/{ci_id}")
def update_device(ci_id:int,data:dict,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user);x=db.get(DispositivoCI,ci_id)
    if not x:raise HTTPException(404,"CI no encontrado")
    if data.get("clasificacion_id") and not db.get(ClasificacionCI,data["clasificacion_id"]):raise HTTPException(422,"Clasificación inexistente")
    if data.get("responsable_id") and not db.get(Usuario,data["responsable_id"]):raise HTTPException(422,"Responsable inexistente")
    allowed={"etiqueta","nombre","clasificacion_id","estado","ubicacion","responsable_id","numero_serie","version","nivel_seguridad","cumplimiento","estado_configuracion","licencia","atributos","activo"}
    for k in allowed&data.keys():setattr(x,k,data[k])
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,"Etiqueta o serie duplicada")
    return device_dict(x)


@router.post("/cmdb/dispositivos/{ci_id}/servicios/{service_id}",status_code=201)
def link_service(ci_id:int,service_id:int,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user)
    if not db.get(DispositivoCI,ci_id) or not db.get(ServicioNivel2,service_id):raise HTTPException(422,"CI o servicio inexistente")
    x=ServicioCI(ci_id=ci_id,servicio_id=service_id);db.add(x)
    try:db.commit();db.refresh(x)
    except IntegrityError:db.rollback();raise HTTPException(409,"Vínculo duplicado")
    return {"id":x.id}


def relation_path(db:Session,start:int,target:int,types:set[str])->bool:
    pending=[start];seen=set()
    while pending:
        cur=pending.pop()
        if cur==target:return True
        if cur in seen:continue
        seen.add(cur);pending.extend(db.scalars(select(RelacionCI.destino_id).where(RelacionCI.origen_id==cur,RelacionCI.tipo.in_(types))))
    return False


@router.post("/cmdb/relaciones",status_code=201)
def create_relation(p:RelacionCIIn,user:Usuario=Depends(mutation_user),db:Session=Depends(get_db)):
    admin(user)
    if p.origen_id==p.destino_id or not db.get(DispositivoCI,p.origen_id) or not db.get(DispositivoCI,p.destino_id):raise HTTPException(422,"CI inválido")
    acyclic=p.tipo in RELACIONES_ACICLICAS or not p.permite_ciclo
    if acyclic and relation_path(db,p.destino_id,p.origen_id,{p.tipo}):raise HTTPException(409,"La relación produciría un ciclo no permitido")
    x=RelacionCI(**p.model_dump());db.add(x)
    try:db.commit();db.refresh(x)
    except IntegrityError:db.rollback();raise HTTPException(409,"Relación duplicada")
    return {"id":x.id}


@router.get("/cmdb/dispositivos/{ci_id}")
def device_detail(ci_id:int,user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    x=db.get(DispositivoCI,ci_id)
    if not x:raise HTTPException(404,"CI no encontrado")
    d=device_dict(x);chain=[];c=x.clasificacion
    while c:chain.insert(0,{"id":c.id,"nombre":c.nombre});c=c.padre
    d["clasificacion_completa"]=chain
    d["relaciones"]=[{"id":r.id,"origen_id":r.origen_id,"destino_id":r.destino_id,"tipo":r.tipo,"permite_ciclo":r.permite_ciclo} for r in db.scalars(select(RelacionCI).where(or_(RelacionCI.origen_id==x.id,RelacionCI.destino_id==x.id)))]
    d["servicio_ids"]=list(db.scalars(select(ServicioCI.servicio_id).where(ServicioCI.ci_id==x.id)))
    d["tickets"]=[{"id":t.id,"numero":t.numero,"estado":t.estado} for t in db.scalars(select(Ticket).join(TicketCI,TicketCI.ticket_id==Ticket.id).where(TicketCI.ci_id==x.id).order_by(Ticket.id.desc()).limit(100))]
    return d


@router.get("/cmdb/dispositivos/{ci_id}/impacto")
def impact(ci_id:int,user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    if not db.get(DispositivoCI,ci_id):raise HTTPException(404,"CI no encontrado")
    pending=[ci_id];seen=set();edges=[]
    while pending and len(seen)<1000:
        cur=pending.pop()
        if cur in seen:continue
        seen.add(cur)
        for r in db.scalars(select(RelacionCI).where(RelacionCI.origen_id==cur,RelacionCI.tipo.in_({"depende_de","alojado_en"}))):edges.append({"origen":r.origen_id,"destino":r.destino_id,"tipo":r.tipo});pending.append(r.destino_id)
    services=list(db.scalars(select(ServicioCI.servicio_id).where(ServicioCI.ci_id.in_(seen))))
    return {"ci_recorridos":sorted(seen),"relaciones":edges,"servicios_potencialmente_afectados":sorted(set(services)),"advertencia":"Una dependencia indica impacto potencial, no prueba una interrupción efectiva."}


@router.get("/tablero")
def dashboard(user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    base=select(Ticket)
    if user.rol!="administrador":base=base.where(or_(Ticket.solicitante_id==user.id,Ticket.responsable_id==user.id))
    rows=db.scalars(base).all();now=utcnow()
    def mins(a,b):
        if not a:return None
        if a.tzinfo is None:a=a.replace(tzinfo=timezone.utc)
        if b.tzinfo is None:b=b.replace(tzinfo=timezone.utc)
        return round((b-a).total_seconds()/60,2)
    group=lambda key:{str(v):sum(1 for x in rows if getattr(x,key)==v) for v in {getattr(x,key) for x in rows}}
    first=[mins(x.creado_en,x.primera_atencion_en) for x in rows if x.primera_atencion_en]
    resolved=[mins(x.creado_en,x.resuelto_en) for x in rows if x.resuelto_en]
    return {"total":len(rows),"por_cola":group("cola_id"),"por_proceso":group("proceso"),"por_prioridad":group("prioridad"),"por_estado":group("estado"),
        "antiguedad_abiertos_min":[{"numero":x.numero,"minutos":mins(x.creado_en,now)} for x in rows if x.estado!="cerrado"],
        "primera_atencion_promedio_min":round(sum(first)/len(first),2) if first else None,"resolucion_promedio_min":round(sum(resolved)/len(resolved),2) if resolved else None,
        "metodo":"tiempo calendario desde creación; abiertos solo en antigüedad; pausas no se descuentan; reapertura reinicia resolución y conserva contador"}


@router.get("/conocimiento")
def knowledge(q:str|None=None,user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    stmt=select(ArticuloConocimiento).where(ArticuloConocimiento.activo.is_(True))
    if q:stmt=stmt.where(or_(ArticuloConocimiento.titulo.ilike(f"%{q}%"),ArticuloConocimiento.contenido.ilike(f"%{q}%")))
    return [{"id":x.id,"titulo":x.titulo,"contenido":x.contenido,"etiquetas":x.etiquetas} for x in db.scalars(stmt.order_by(ArticuloConocimiento.titulo))]


@router.get("/notificaciones")
def notifications(user:Usuario=Depends(get_current_user),db:Session=Depends(get_db)):
    return [{"id":x.id,"ticket_id":x.ticket_id,"canal":x.canal,"mensaje":x.mensaje,"creado_en":x.creado_en,"leida_en":x.leida_en} for x in db.scalars(select(Notificacion).where(or_(Notificacion.destinatario_id==user.id,Notificacion.destinatario_id.is_(None))).order_by(Notificacion.id.desc()).limit(100))]

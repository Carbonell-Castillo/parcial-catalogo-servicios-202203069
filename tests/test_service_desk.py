from concurrent.futures import ThreadPoolExecutor

from app.demo import generate_cmdb
from app.models import DispositivoCI, Ticket
from tests.conftest import do_login


def setup_domain(admin, db):
    c,h=admin["client"],admin["headers"]
    n1=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"SD","nombre":"Service Desk"}).json()
    svc=c.post("/api/servicios",headers=h,json={"codigo":"SD.1","nombre":"Atención TI","nivel1_id":n1["id"]}).json()
    reader=db.execute(__import__("sqlalchemy").select(__import__("app.models",fromlist=["Usuario"]).Usuario).where(__import__("app.models",fromlist=["Usuario"]).Usuario.login=="consulta")).scalar_one()
    queues={}
    for i,p in enumerate(["nuevos_servicios","cambios","incidentes","eventos","problemas","accesos","servicios_tecnologia"],1):
        q=c.post("/api/colas",headers=h,json={"codigo":f"TQ{i}","nombre":p,"proceso":p}).json();queues[p]=q
        c.post(f"/api/colas/{q['id']}/miembros",headers=h,json={"usuario_id":reader.id,"puede_consultar":True})
    root=c.post("/api/cmdb/clasificaciones",headers=h,json={"codigo":"ROOT","nombre":"CI"}).json()
    child=c.post("/api/cmdb/clasificaciones",headers=h,json={"codigo":"HW","nombre":"Hardware","padre_id":root["id"]}).json()
    ci=c.post("/api/cmdb/dispositivos",headers=h,json={"etiqueta":"CI-TEST-1","nombre":"Servidor prueba","clasificacion_id":child["id"],"estado":"Activo","ubicacion":"Laboratorio"}).json()
    return c,h,svc,queues,root,child,ci,reader


def make_ticket(c,h,svc,q,process,requester=None,data=None,ci=None):
    body={"titulo":f"Prueba {process}","descripcion":"Descripción controlada","servicio_id":svc["id"],"proceso":process,"cola_id":q["id"],"datos_proceso":data or {}}
    if requester:body["solicitante_id"]=requester
    if ci:body["ci_ids"]=[ci]
    else:body["sin_ci_justificacion"]="Trámite que no afecta un dispositivo"
    return c.post("/api/tickets",headers=h,json=body)


def test_p05_valid_and_invalid_ticket_references(admin,db):
    c,h,svc,qs,*rest=setup_domain(admin,db)
    assert make_ticket(c,h,svc,qs["accesos"],"accesos").status_code==201
    bad=make_ticket(c,h,{"id":99999},qs["accesos"],"accesos")
    assert bad.status_code==422
    wrong=make_ticket(c,h,svc,qs["incidentes"],"accesos")
    assert wrong.status_code==422


def test_p06_queue_permissions_and_consulta_not_elevated(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db)
    t=make_ticket(c,h,svc,qs["servicios_tecnologia"],"servicios_tecnologia",reader.id,ci=ci["id"]).json()
    login=do_login(c,"consulta","Reader-Test-2026!");rh={"X-CSRF-Token":login.json()["csrf"]}
    assert c.get("/api/tickets").status_code==200
    assert c.post(f"/api/tickets/{t['id']}/tomar",headers=rh).status_code==403
    ah={"X-CSRF-Token":do_login(c).json()["csrf"]}
    assert c.post(f"/api/colas/{qs['accesos']['id']}/miembros",headers=ah,json={"usuario_id":reader.id,"puede_consultar":True,"puede_atender":True}).status_code==200


def test_p07_deterministic_order_and_single_claim(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db);q=qs["incidentes"]
    c.post(f"/api/colas/{q['id']}/miembros",headers=h,json={"usuario_id":reader.id,"puede_consultar":True,"puede_atender":True})
    low=make_ticket(c,h,svc,q,"incidentes",data={"categoria":"I0"},ci=ci["id"]).json()
    critical=make_ticket(c,h,svc,q,"incidentes",data={"categoria":"I1"},ci=ci["id"]).json()
    db.get(Ticket,critical["id"]).prioridad="critica";db.commit()
    assert c.get("/api/tickets").json()["items"][0]["id"]==critical["id"]
    login=do_login(c,"consulta","Reader-Test-2026!");rh={"X-CSRF-Token":login.json()["csrf"]}
    assert c.post(f"/api/tickets/{low['id']}/tomar",headers=rh).status_code==200
    ah={"X-CSRF-Token":do_login(c).json()["csrf"]}
    assert c.post(f"/api/tickets/{low['id']}/tomar",headers=ah).status_code==409


def test_p08_transfer_history_and_process_validation(admin,db):
    c,h,svc,qs,*_=setup_domain(admin,db)
    second=c.post("/api/colas",headers=h,json={"codigo":"TQ8","nombre":"Incidentes L2","proceso":"incidentes","nivel_soporte":2}).json()
    t=make_ticket(c,h,svc,qs["incidentes"],"incidentes",data={"categoria":"I0"}).json()
    assert c.post(f"/api/tickets/{t['id']}/transferir",headers=h,json={"cola_id":qs["accesos"]["id"],"motivo":"Destino incorrecto"}).status_code==422
    assert c.post(f"/api/tickets/{t['id']}/transferir",headers=h,json={"cola_id":second["id"],"motivo":"Escalamiento técnico"}).status_code==200
    detail=c.get(f"/api/tickets/{t['id']}").json()
    assert any(x["accion"]=="transferencia" and x["motivo"]=="Escalamiento técnico" for x in detail["historial"])


def test_p09_complete_route_for_all_processes_and_invalid_transition(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db)
    initial={"incidentes":{"categoria":"I1","interrupcion":True,"redundancia":"disponible","justificacion_categoria":"Manual"},"eventos":{"categoria":"E0"}}
    evidence={
        ("nuevos_servicios","analisis"):{"necesidad":"Existe demanda","viabilidad":"Viable"},
        ("cambios","evaluacion"):{"impacto":"medio","riesgo":"bajo","plan_pruebas":"automatizado","plan_reversion":"rollback"},
        ("incidentes","clasificacion"):initial["incidentes"],
        ("problemas","causa_raiz"):{"causa_raiz":"Configuración incorrecta"},
        ("accesos","aprobado"):{"beneficiario_id":reader.id,"recurso":"Portal","permiso":"lectura"},
        ("servicios_tecnologia","cumplimiento"):{"resultado_cumplimiento":"Entregado"},
    }
    config=c.get("/api/service-desk/configuracion").json()["procesos"]
    for process,flow in config.items():
        t=make_ticket(c,h,svc,qs[process],process,reader.id,initial.get(process),ci["id"]).json()
        assert c.post(f"/api/tickets/{t['id']}/transiciones",headers=h,json={"estado":"cerrado"}).status_code==409
        for target in flow[1:]:
            r=c.post(f"/api/tickets/{t['id']}/transiciones",headers=h,json={"estado":target,"datos":evidence.get((process,target),{})})
            assert r.status_code==200,(process,target,r.text)


def test_p10_change_without_approval_and_access_selfapproval(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db)
    change=make_ticket(c,h,svc,qs["cambios"],"cambios",reader.id,ci=ci["id"]).json()
    assert c.post(f"/api/tickets/{change['id']}/transiciones",headers=h,json={"estado":"ejecucion"}).status_code==409
    access=make_ticket(c,h,svc,qs["accesos"],"accesos",reader.id,ci=ci["id"]).json()
    c.post(f"/api/colas/{qs['accesos']['id']}/miembros",headers=h,json={"usuario_id":reader.id,"puede_consultar":True,"puede_atender":True,"puede_aprobar":True})
    login=do_login(c,"consulta","Reader-Test-2026!");rh={"X-CSRF-Token":login.json()["csrf"]}
    r=c.post(f"/api/tickets/{access['id']}/transiciones",headers=rh,json={"estado":"aprobado","datos":{"beneficiario_id":reader.id,"recurso":"X","permiso":"Y"}})
    assert r.status_code==409


def test_p11_events_and_incident_idempotency(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db)
    for category in ["E0","E1","E2","E3"]:
        t=make_ticket(c,h,svc,qs["eventos"],"eventos",reader.id,{"categoria":category},ci["id"]).json()
        for state in ["clasificacion","evaluacion","respuesta"]:assert c.post(f"/api/tickets/{t['id']}/transiciones",headers=h,json={"estado":state}).status_code==200
        d=c.get(f"/api/tickets/{t['id']}").json()
        generated=[x for x in d["historial"] if x["accion"]=="incidente_generado"]
        if category in {"E2","E3"}:assert db.query(Ticket).filter(Ticket.proceso=="incidentes",Ticket.canal=="evento").count()>=1


def test_p12_i0_i6_and_complementary_duration_rule(admin,db):
    c,h,svc,qs,*_=setup_domain(admin,db)
    for i in range(7):
        data={"categoria":f"I{i}"}
        if i==6:data["seguridad"]=True
        assert make_ticket(c,h,svc,qs["incidentes"],"incidentes",data=data).status_code==201
    bad=make_ticket(c,h,svc,qs["incidentes"],"incidentes",data={"categoria":"I2","duracion_estimada_min":120})
    assert bad.status_code==422


def test_p13_incident_problem_change_traceability(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db)
    incident=make_ticket(c,h,svc,qs["incidentes"],"incidentes",reader.id,{"categoria":"I1"},ci["id"]).json()
    problem=make_ticket(c,h,svc,qs["problemas"],"problemas",reader.id,ci=ci["id"]).json()
    change=make_ticket(c,h,svc,qs["cambios"],"cambios",reader.id,ci=ci["id"]).json()
    assert c.post(f"/api/tickets/{incident['id']}/relaciones",headers=h,json={"relacionado_id":problem["id"],"tipo":"origina_problema"}).status_code==201
    assert c.post(f"/api/tickets/{problem['id']}/relaciones",headers=h,json={"relacionado_id":change["id"],"tipo":"corregido_por_cambio"}).status_code==201
    assert any(x["relacionado_id"]==change["id"] for x in c.get(f"/api/tickets/{problem['id']}").json()["relaciones"])


def test_p14_cmdb_cycles_traversal_and_p16_pagination(admin,db):
    c,h,svc,qs,root,child,ci,_=setup_domain(admin,db)
    assert c.patch(f"/api/cmdb/clasificaciones/{root['id']}",headers=h,json={"padre_id":child["id"]}).status_code==409
    other=c.post("/api/cmdb/dispositivos",headers=h,json={"etiqueta":"CI-TEST-2","nombre":"Aplicación","clasificacion_id":child["id"],"estado":"Activo","ubicacion":"Laboratorio"}).json()
    assert c.post("/api/cmdb/relaciones",headers=h,json={"origen_id":ci["id"],"destino_id":other["id"],"tipo":"depende_de"}).status_code==201
    assert c.post("/api/cmdb/relaciones",headers=h,json={"origen_id":other["id"],"destino_id":ci["id"],"tipo":"depende_de"}).status_code==409
    assert c.post(f"/api/cmdb/dispositivos/{other['id']}/servicios/{svc['id']}",headers=h).status_code==201
    impact=c.get(f"/api/cmdb/dispositivos/{ci['id']}/impacto").json();assert svc["id"] in impact["servicios_potencialmente_afectados"]
    result=generate_cmdb(db,5000,777);assert result["total_con_semilla"]==5000
    again=generate_cmdb(db,5000,777);assert again["creados"]==0
    page=c.get("/api/cmdb/dispositivos?page=2&size=100").json();assert page["total"]>=5000 and len(page["items"])==100


def test_p15_close_reopen_audit_and_p17_indicators(admin,db):
    c,h,svc,qs,_,_,ci,reader=setup_domain(admin,db)
    t=make_ticket(c,h,svc,qs["servicios_tecnologia"],"servicios_tecnologia",reader.id,ci=ci["id"]).json()
    assert c.post(f"/api/tickets/{t['id']}/transiciones",headers=h,json={"estado":"cerrado"}).status_code==409
    for state in ["validacion","asignacion","cumplimiento","confirmacion","resuelto","cerrado"]:
        data={"resultado_cumplimiento":"Listo"} if state=="cumplimiento" else {}
        assert c.post(f"/api/tickets/{t['id']}/transiciones",headers=h,json={"estado":state,"datos":data}).status_code==200
    assert c.post(f"/api/tickets/{t['id']}/transiciones",headers=h,json={"estado":"reabierto","motivo":"Reincidencia"}).status_code==200
    detail=c.get(f"/api/tickets/{t['id']}").json();assert detail["reaperturas"]==1 and any(x["actor_id"] for x in detail["historial"])
    board=c.get("/api/tablero").json();assert board["total"]>=1 and "pausas" in board["metodo"]

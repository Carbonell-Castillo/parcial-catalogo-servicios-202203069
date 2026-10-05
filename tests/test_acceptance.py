from tests.conftest import do_login

def create_hierarchy(ctx, prefix="A"):
    c,h=ctx["client"],ctx["headers"]
    company=c.post("/api/organizacion/empresas",headers=h,json={"codigo":prefix+"EMP","nombre":"Empresa"}).json()
    area=c.post("/api/organizacion/areas",headers=h,json={"codigo":"AR","nombre":"Área","parent_id":company["id"]}).json()
    dep=c.post("/api/organizacion/departamentos",headers=h,json={"codigo":"DEP","nombre":"Departamento","parent_id":area["id"]}).json()
    sec=c.post("/api/organizacion/secciones",headers=h,json={"codigo":"SEC","nombre":"Sección","parent_id":dep["id"]}).json()
    pos=c.post("/api/organizacion/puestos",headers=h,json={"codigo":"PUE","nombre":"Puesto","parent_id":sec["id"]}).json()
    return company,area,dep,sec,pos

def test_p01_login_valid_and_invalid(client):
    assert do_login(client).status_code == 200
    assert do_login(client,"admin","incorrecta").status_code == 401

def test_p02_unauth_logout_and_inactive(client):
    assert client.get("/api/servicios").status_code == 401
    logged=do_login(client); csrf=logged.json()["csrf"]
    assert client.post("/api/auth/logout",headers={"X-CSRF-Token":csrf}).status_code == 200
    assert client.get("/api/servicios").status_code == 401
    assert do_login(client,"inactivo","Inactive-Test-2026!").status_code == 401

def test_p03_reader_cannot_modify_but_can_read(reader):
    c,h=reader["client"],reader["headers"]
    assert c.get("/api/servicios").status_code == 200
    assert c.post("/api/organizacion/empresas",headers=h,json={"codigo":"X","nombre":"X"}).status_code == 403

def test_csrf_is_required_and_hashes_are_never_returned(admin):
    c,h=admin["client"],admin["headers"]
    assert c.post("/api/organizacion/empresas",json={"codigo":"CSRF","nombre":"CSRF"}).status_code == 403
    response=c.get("/api/usuarios",headers=h)
    assert response.status_code==200
    assert all("password_hash" not in item for item in response.json())

def test_p04_hierarchy_and_user(admin):
    _,_,_,_,pos=create_hierarchy(admin)
    r=admin["client"].post("/api/usuarios",headers=admin["headers"],json={"nombre":"Ana","login":"ana@example.test","password":"Strong-Test-123!","rol":"consulta","puesto_id":pos["id"]})
    assert r.status_code == 201 and r.json()["puesto_id"] == pos["id"]

def test_p05_duplicate_and_missing_parent(admin):
    c,h=admin["client"],admin["headers"]
    assert c.post("/api/organizacion/empresas",headers=h,json={"codigo":"DUP","nombre":"Uno"}).status_code == 201
    assert c.post("/api/organizacion/empresas",headers=h,json={"codigo":"DUP","nombre":"Dos"}).status_code == 409
    assert c.post("/api/organizacion/areas",headers=h,json={"codigo":"A","nombre":"A","parent_id":999}).status_code == 422

def test_p09_minimum_cannot_exceed_maximum(admin):
    c,h=admin["client"],admin["headers"]
    n1=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"N1","nombre":"Nivel"}).json()
    r=c.post("/api/servicios",headers=h,json={"codigo":"N2","nombre":"Servicio","nivel1_id":n1["id"],"minimo":"20","maximo":"10"})
    assert r.status_code == 422

def test_p10_search_filter_and_pagination(admin):
    c,h=admin["client"],admin["headers"]
    n1=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"BUS","nombre":"Buscable"}).json()
    for i in range(3): assert c.post("/api/servicios",headers=h,json={"codigo":f"S.{i}","nombre":f"Correo {i}","nivel1_id":n1["id"]}).status_code==201
    result=c.get(f"/api/servicios?q=Correo&nivel1_id={n1['id']}&size=2&page=2").json()
    assert result["total"]==3 and len(result["items"])==1 and result["pages"]==2

def test_p11_responsible_must_belong_to_section(admin):
    c,h=admin["client"],admin["headers"]
    *_,sec1,pos1=create_hierarchy(admin,"A")
    *_,sec2,pos2=create_hierarchy(admin,"B")
    user=c.post("/api/usuarios",headers=h,json={"nombre":"Resp","login":"resp","password":"Strong-Test-123!","rol":"consulta","puesto_id":pos1["id"]}).json()
    n1=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"R1","nombre":"Responsables"}).json()
    r=c.post("/api/servicios",headers=h,json={"codigo":"R2","nombre":"Servicio","nivel1_id":n1["id"],"seccion_responsable_id":sec2["id"],"usuario_responsable_id":user["id"]})
    assert r.status_code==422 and "sección" in r.json()["detail"]

def test_inactive_parent_and_dependency_policy(admin):
    c,h=admin["client"],admin["headers"]
    company,*_=create_hierarchy(admin)
    assert c.patch(f"/api/organizacion/empresas/{company['id']}",headers=h,json={"activo":False}).status_code==409
    empty=c.post("/api/organizacion/empresas",headers=h,json={"codigo":"EMPTY","nombre":"Vacía"}).json()
    assert c.patch(f"/api/organizacion/empresas/{empty['id']}",headers=h,json={"activo":False}).status_code==200
    assert c.post("/api/organizacion/areas",headers=h,json={"codigo":"NO","nombre":"No","parent_id":empty["id"]}).status_code==422

def test_level1_crud_and_active_dependency_policy(admin):
    c,h=admin["client"],admin["headers"]
    item=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"L1","nombre":"Original"})
    assert item.status_code==201
    item=item.json()
    updated=c.patch(f"/api/servicios/nivel1/{item['id']}",headers=h,json={"nombre":"Actualizado"})
    assert updated.status_code==200 and updated.json()["nombre"]=="Actualizado"
    assert c.patch(f"/api/servicios/nivel1/{item['id']}",headers=h,json={"activo":False}).status_code==200
    assert any(row["id"]==item["id"] and not row["activo"] for row in c.get("/api/servicios/nivel1?include_inactive=true",headers=h).json())
    parent=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"L2","nombre":"Con hijo"}).json()
    assert c.post("/api/servicios",headers=h,json={"codigo":"L2.1","nombre":"Servicio","nivel1_id":parent["id"]}).status_code==201
    blocked=c.patch(f"/api/servicios/nivel1/{parent['id']}",headers=h,json={"activo":False})
    assert blocked.status_code==409 and "servicios nivel 2 activos" in blocked.json()["detail"]

def test_service_detail_includes_responsible_names(admin):
    c,h=admin["client"],admin["headers"]
    *_,section,position=create_hierarchy(admin,"D")
    user=c.post("/api/usuarios",headers=h,json={"nombre":"Responsable Visible","login":"visible","password":"Strong-Test-123!","rol":"consulta","puesto_id":position["id"]}).json()
    level1=c.post("/api/servicios/nivel1",headers=h,json={"codigo":"DET","nombre":"Detalle"}).json()
    service=c.post("/api/servicios",headers=h,json={"codigo":"DET.1","nombre":"Servicio","nivel1_id":level1["id"],"seccion_responsable_id":section["id"],"usuario_responsable_id":user["id"]}).json()
    detail=c.get(f"/api/servicios/{service['id']}",headers=h)
    assert detail.status_code==200
    assert detail.json()["seccion_responsable"]=="Sección"
    assert detail.json()["usuario_responsable"]=="Responsable Visible"

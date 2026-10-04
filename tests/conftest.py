import os
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test-secret-only"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.database import get_db
from app.main import app
from app.models import Base, ClaseServicio, Criticidad, TipoServicio, Usuario
from app.security import hash_password

@pytest.fixture()
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        session.add_all([
            ClaseServicio(codigo="CL-01", nombre="A DEMANDA"), ClaseServicio(codigo="CL-02", nombre="RECURRENTE"),
            Criticidad(codigo="CR-01", nombre="Normal"), TipoServicio(codigo="TP-01", nombre="Back End"),
            Usuario(nombre="Admin", login="admin", password_hash=hash_password("Admin-Test-2026!"), rol="administrador"),
            Usuario(nombre="Reader", login="consulta", password_hash=hash_password("Reader-Test-2026!"), rol="consulta"),
            Usuario(nombre="Inactive", login="inactivo", password_hash=hash_password("Inactive-Test-2026!"), rol="consulta", activo=False),
        ]); session.commit()
        yield session

@pytest.fixture()
def client(db):
    def override(): yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()

def do_login(client, login="admin", password="Admin-Test-2026!"):
    response = client.post("/api/auth/login", json={"login": login, "password": password})
    return response

@pytest.fixture()
def admin(client):
    response = do_login(client)
    assert response.status_code == 200
    return {"client": client, "headers": {"X-CSRF-Token": response.json()["csrf"]}}

@pytest.fixture()
def reader(client):
    response = do_login(client, "consulta", "Reader-Test-2026!")
    assert response.status_code == 200
    return {"client": client, "headers": {"X-CSRF-Token": response.json()["csrf"]}}


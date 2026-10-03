import argparse
import os
from pathlib import Path
from sqlalchemy import select
from app.database import SessionLocal
from app.importer import import_excel
from app.models import (Area, ClaseServicio, Criticidad, Departamento, Empresa,
    Puesto, Seccion, ServicioNivel2, TipoServicio, Usuario)
from app.security import hash_password

CATALOGS = {
    ClaseServicio: ["A DEMANDA", "RECURRENTE"],
    Criticidad: ["Very Low", "Low", "Normal", "High", "Very High"],
    TipoServicio: ["Back End", "Demostration", "End User Service", "Front End", "IT Management", "IT Operational", "Other", "Project", "Reporting", "Training", "Underpinning Contract"],
}

def ensure_demo(db, assign_services: bool = False):
        company = db.scalar(select(Empresa).where(Empresa.codigo == "DEMO"))
        if not company: company=Empresa(codigo="DEMO", nombre="Empresa de demostración"); db.add(company); db.flush()
        area = db.scalar(select(Area).where(Area.empresa_id == company.id, Area.codigo == "TI"))
        if not area: area=Area(codigo="TI", nombre="Tecnología", empresa_id=company.id); db.add(area); db.flush()
        department = db.scalar(select(Departamento).where(Departamento.area_id == area.id, Departamento.codigo == "OPS"))
        if not department: department=Departamento(codigo="OPS", nombre="Operaciones", area_id=area.id); db.add(department); db.flush()
        section = db.scalar(select(Seccion).where(Seccion.departamento_id == department.id, Seccion.codigo == "SOP"))
        if not section: section=Seccion(codigo="SOP", nombre="Soporte de servicios", departamento_id=department.id); db.add(section); db.flush()
        position = db.scalar(select(Puesto).where(Puesto.seccion_id == section.id, Puesto.codigo == "RESP"))
        if not position: position=Puesto(codigo="RESP", nombre="Responsable de servicio", seccion_id=section.id); db.add(position); db.flush()
        if assign_services:
            responsible = db.scalar(select(Usuario).where(Usuario.login == "consulta"))
            if responsible:
                responsible.puesto_id = position.id
                for service in db.scalars(select(ServicioNivel2).order_by(ServicioNivel2.codigo).limit(3)):
                    service.seccion_responsable_id = section.id
                    service.usuario_responsable_id = responsible.id
        return section, position

def seed():
    with SessionLocal() as db:
        for model, names in CATALOGS.items():
            for index, name in enumerate(names, 1):
                if not db.scalar(select(model).where(model.nombre == name)):
                    db.add(model(codigo=f"{model.__tablename__.upper()}-{index:02d}", nombre=name))
        accounts = [
            ("Administrador Demo", "admin", os.getenv("DEMO_ADMIN_PASSWORD", "Admin-Demo-2026!"), "administrador"),
            ("Consulta Demo", "consulta", os.getenv("DEMO_READER_PASSWORD", "Consulta-Demo-2026!"), "consulta"),
        ]
        for name, login, password, role in accounts:
            if not db.scalar(select(Usuario).where(Usuario.login == login)):
                db.add(Usuario(nombre=name, login=login, password_hash=hash_password(password), rol=role))
        db.flush()
        _, position = ensure_demo(db)
        reader = db.scalar(select(Usuario).where(Usuario.login == "consulta"))
        if reader and reader.puesto_id is None: reader.puesto_id = position.id
        db.commit()
    print("Catálogos y cuentas demo listos")

def main():
    parser = argparse.ArgumentParser(description="Operaciones reproducibles del catálogo")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed")
    imp = commands.add_parser("import")
    imp.add_argument("path", nargs="?", default="data/CatalogoServicios.xlsx")
    args = parser.parse_args()
    if args.command == "seed": seed()
    elif args.command == "import":
        with SessionLocal() as db:
            result = import_excel(db, Path(args.path))
            ensure_demo(db, assign_services=True); db.commit()
            print(result.dict())

if __name__ == "__main__": main()

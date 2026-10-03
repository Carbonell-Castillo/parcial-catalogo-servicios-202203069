import hashlib
import hmac
import os
import secrets
from datetime import timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Sesion, Usuario, utcnow

hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)
COOKIE_NAME = "catalogo_session"
SESSION_HOURS = 8

def hash_password(password: str) -> str:
    return hasher.hash(password)

def verify_password(password: str, encoded: str) -> bool:
    try:
        return hasher.verify(encoded, password)
    except (VerificationError, ValueError, TypeError):
        return False

def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def csrf_for(token: str) -> str:
    secret = os.getenv("SESSION_SECRET", "desarrollo-local-cambiar-esta-clave").encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()

def create_session(db: Session, user: Usuario) -> str:
    token = secrets.token_urlsafe(48)
    db.add(Sesion(token_hash=token_hash(token), usuario_id=user.id, expira_en=utcnow() + timedelta(hours=SESSION_HOURS)))
    db.commit()
    return token

def get_current_user(request: Request, db: Session = Depends(get_db)) -> Usuario:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión requerida")
    session = db.scalar(select(Sesion).where(Sesion.token_hash == token_hash(token)))
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")
    expires = session.expira_en
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if session.revocada_en is not None or expires <= utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sesión inválida o expirada")
    if not session.usuario.activo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")
    request.state.session_token = token
    return session.usuario

def require_admin(request: Request, user: Usuario = Depends(get_current_user)) -> Usuario:
    if user.rol != "administrador":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol administrador")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        supplied = request.headers.get("X-CSRF-Token", "")
        if not hmac.compare_digest(supplied, csrf_for(request.state.session_token)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token CSRF inválido")
    return user

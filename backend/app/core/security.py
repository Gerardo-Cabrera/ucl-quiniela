from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.config import settings

# bcrypt solo usa los primeros 72 BYTES de la contraseña. Se truncan explícitamente
# (en bytes UTF-8) por dos motivos: es lo que hacía passlib, así los hashes ya
# guardados ($2b$12$...) siguen verificando igual; y bcrypt >= 5 lanza ValueError en
# vez de truncar en silencio, con lo que el límite deja de depender de la versión
# instalada. El schema limita además a 72 caracteres (uno puede ocupar varios bytes).
# Se usa bcrypt directo (sin passlib: sin mantenimiento desde 2020, importa `crypt`,
# eliminado en Python 3.13, y obligaba a fijar bcrypt en 4.0.x).
_BCRYPT_MAX_BYTES = 72


def _secret(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    # gensalt(): 12 rondas, prefijo $2b$ (los mismos valores por defecto que passlib).
    return bcrypt.hashpw(_secret(password), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_secret(plain), hashed.encode("ascii"))
    except ValueError:
        # Hash que no es bcrypt (p. ej. una fila sembrada a mano): credencial
        # inválida, no un 500.
        return False


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

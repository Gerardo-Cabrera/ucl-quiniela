from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas import UserCreate, UserLogin, UserOut, Token, PasswordChange, PasswordReset
from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.config import settings
from app.crud import user_crud

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def register(request: Request, data: UserCreate, db: AsyncSession = Depends(get_db)):
    # El nombre de equipo es libre; se rechaza solo si email, equipo o alias ya existen.
    conflict = await user_crud.get_conflict(
        db, email=data.email, team_name=data.team_name, alias=data.alias
    )
    if conflict:
        if conflict.email == data.email:
            detail = "Ese email ya está registrado."
        elif conflict.team_name == data.team_name:
            detail = "Ese nombre de equipo ya está en uso."
        else:
            detail = "Ese alias ya está en uso."
        raise HTTPException(status_code=409, detail=detail)

    user = await user_crud.create(
        db,
        team_name=data.team_name,
        email=data.email,
        alias=data.alias,
        hashed_password=hash_password(data.password),
    )
    return user


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def login(request: Request, data: UserLogin, db: AsyncSession = Depends(get_db)):
    # El identificador puede ser el email, el alias o el nombre de equipo.
    user = await user_crud.get_by_identifier(db, data.identifier)

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas.")

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/change-password", response_model=UserOut)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def change_password(
    request: Request,
    data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cambia la contraseña del usuario autenticado (verifica la actual)."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta.")
    if data.new_password == data.current_password:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe ser distinta de la actual.")
    await user_crud.update_password(db, current_user, hashed_password=hash_password(data.new_password))
    return current_user


@router.post("/reset-password", status_code=204)
@limiter.limit(settings.RATE_LIMIT_AUTH)
async def reset_password(
    request: Request,
    data: PasswordReset,
    db: AsyncSession = Depends(get_db),
):
    """Recuperación sin email: prueba la identidad con email + nombre de equipo
    (ambos únicos) y define la nueva contraseña. Limitada por tasa (anti fuerza bruta)."""
    user = await user_crud.get_by_email_and_team(db, data.email, data.team_name)
    if not user:
        raise HTTPException(status_code=400, detail="Los datos no coinciden con ninguna cuenta.")
    await user_crud.update_password(db, user, hashed_password=hash_password(data.new_password))

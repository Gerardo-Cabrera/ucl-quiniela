from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import UserCreate, UserLogin, UserOut, Token
from app.core.security import hash_password, verify_password, create_access_token
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

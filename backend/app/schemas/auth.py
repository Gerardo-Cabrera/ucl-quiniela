from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    # El nombre de equipo es texto libre (mín. 3 caracteres tras recortar espacios).
    team_name: str = Field(max_length=100)
    email: EmailStr
    password: str = Field(max_length=72)
    # Alias/nombre de usuario opcional (mín. 3 si se indica).
    alias: Optional[str] = Field(default=None, max_length=100)

    @field_validator("team_name")
    @classmethod
    def _validate_team_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("El nombre de equipo debe tener al menos 3 caracteres.")
        return v

    @field_validator("alias")
    @classmethod
    def _validate_alias(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:            # alias en blanco → sin alias
            return None
        if len(v) < 3:
            raise ValueError("El alias debe tener al menos 3 caracteres.")
        return v

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        # max 72: bcrypt trunca silenciosamente los bytes restantes.
        if len(v) < 6:
            raise ValueError("La contraseña debe tener al menos 6 caracteres.")
        return v


class UserLogin(BaseModel):
    # Identificador: email, alias o nombre de equipo.
    identifier: str = Field(min_length=1)
    password: str


class UserOut(BaseModel):
    id: int
    team_name: str
    alias: Optional[str]
    email: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

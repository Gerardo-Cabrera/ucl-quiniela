from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from app.models.user import User


class UserCRUD:
    async def get_by_team_name(self, db: AsyncSession, team_name: str) -> User | None:
        """Usuario dueño de un nombre de equipo (para validar unicidad al editar el perfil)."""
        result = await db.execute(select(User).where(User.team_name == team_name))
        return result.scalar_one_or_none()

    async def get_by_alias(self, db: AsyncSession, alias: str) -> User | None:
        """Usuario dueño de un alias (para validar unicidad al editar el perfil)."""
        result = await db.execute(select(User).where(User.alias == alias))
        return result.scalar_one_or_none()

    async def find_by_identifier(self, db: AsyncSession, identifier: str) -> list[User]:
        """Candidatos para el login: usuarios cuyo email, alias o nombre de equipo coincide
        con `identifier` SIN distinguir mayúsculas ni espacios alrededor (los teclados
        móviles capitalizan la primera letra y añaden espacios, y el email se guardaba con
        la parte local tal como se escribió). Puede haber más de uno (el alias de A igual
        al equipo de B, o dos equipos que solo difieren en mayúsculas): el login prueba la
        contraseña contra cada uno en vez de quedarse con el primero."""
        value = identifier.strip().lower()
        if not value:
            return []
        result = await db.execute(
            select(User)
            .where(or_(
                func.lower(User.email) == value,
                func.lower(User.alias) == value,
                func.lower(User.team_name) == value,
            ))
            .order_by(User.id)
        )
        return list(result.scalars().all())

    async def get_by_email_and_team(
        self, db: AsyncSession, email: str, team_name: str
    ) -> User | None:
        """Usuario que coincide en email Y nombre de equipo, sin distinguir mayúsculas ni
        espacios alrededor (recuperación de contraseña por datos de la cuenta)."""
        result = await db.execute(
            select(User).where(
                func.lower(User.email) == email.strip().lower(),
                func.lower(User.team_name) == team_name.strip().lower(),
            )
        )
        return result.scalars().first()

    async def update_password(
        self, db: AsyncSession, user: User, *, hashed_password: str
    ) -> User:
        user.hashed_password = hashed_password
        await db.flush()
        await db.refresh(user)
        return user

    async def get_conflict(
        self, db: AsyncSession, *, email: str, team_name: str, alias: str | None
    ) -> User | None:
        """Devuelve el usuario existente que colisione en email, equipo o alias (para
        rechazar el registro). El email se compara sin distinguir mayúsculas (dos cuentas
        no deben diferir solo en eso); equipo y alias, tal cual. El alias solo se compara
        si se indicó."""
        conditions = [func.lower(User.email) == email.lower(), User.team_name == team_name]
        if alias is not None:
            conditions.append(User.alias == alias)
        result = await db.execute(select(User).where(or_(*conditions)))
        return result.scalars().first()

    async def create(
        self, db: AsyncSession, *, team_name: str, email: str, hashed_password: str,
        alias: str | None = None,
    ) -> User:
        user = User(
            team_name=team_name,
            email=email,
            alias=alias,
            hashed_password=hashed_password,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user


user_crud = UserCRUD()

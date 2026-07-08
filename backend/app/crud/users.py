from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from app.models.user import User


class UserCRUD:
    async def get_by_identifier(self, db: AsyncSession, identifier: str) -> User | None:
        """Busca un usuario por email, alias o nombre de equipo (para el login)."""
        result = await db.execute(
            select(User).where(
                or_(
                    User.email == identifier,
                    User.alias == identifier,
                    User.team_name == identifier,
                )
            )
        )
        return result.scalars().first()

    async def get_conflict(
        self, db: AsyncSession, *, email: str, team_name: str, alias: str | None
    ) -> User | None:
        """Devuelve el usuario existente que colisione en email, equipo o alias (para
        rechazar el registro). El alias solo se compara si se indicó."""
        conditions = [User.email == email, User.team_name == team_name]
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

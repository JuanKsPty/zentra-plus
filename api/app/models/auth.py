from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.db.types import TimestampTZ
from app.models.base import ahora_utc


class RefreshToken(SQLModel, table=True):
    """
    Un refresco vivo. Se guarda el `jti`, NO el token.

    Tres motivos, y los tres son mejoras sobre guardar la cadena entera:

    1. Un volcado de la base no contiene credenciales reutilizables. Con el
       token guardado, quien lo lea puede reactivar sesiones ajenas.
    2. La clave son 16 bytes en vez de un texto largo indexado.
    3. `replaced_by` permite DETECTAR REUSO: si llega un refresco cuyo jti esta
       revocado y ademas tiene sucesor, alguien esta reproduciendo un token
       viejo. La respuesta correcta no es rechazar solo ese: es revocar la
       cadena entera y subir el `token_version` del usuario, porque si un token
       antiguo esta circulando, el actual tambien puede estarlo.
    """

    __tablename__ = "refresh_tokens"

    jti: UUID = Field(primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", ondelete="CASCADE", index=True)
    login_method: str = Field(max_length=10)
    expires_at: datetime = Field(sa_type=TimestampTZ)
    revoked_at: datetime | None = Field(default=None, sa_type=TimestampTZ)
    replaced_by: UUID | None = Field(default=None)
    created_at: datetime = Field(default_factory=ahora_utc, sa_type=TimestampTZ)

    @property
    def esta_vivo(self) -> bool:
        return self.revoked_at is None

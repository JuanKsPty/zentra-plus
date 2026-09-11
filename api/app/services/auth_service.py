"""
Iniciar sesion, renovarla y cerrarla.

Dos puertas —correo y PIN— que producen la misma sesion con ventanas distintas,
y una rotacion de refrescos que detecta reuso.
"""

from datetime import UTC, datetime
from uuid import UUID

import jwt
from sqlmodel import Session, col, select

from app.core.config import settings
from app.core.errors import ErrorAplicacion
from app.core.security import (
    MetodoDeAcceso,
    firmar_acceso,
    firmar_refresco,
    leer_refresco,
    verificar,
)
from app.models import Branch, RefreshToken, User, UserBranch

# El mismo mensaje para «no existe», «contrasena incorrecta» y —cuando llegue el
# bloqueo por intentos— «cuenta bloqueada». Distinguirlos le regala al atacante
# un oraculo de que correos estan registrados y cuando volver a intentarlo.
CREDENCIALES_INVALIDAS = "Correo o contrasena incorrectos."
PIN_INVALIDO = "PIN incorrecto."


class SesionEmitida:
    def __init__(self, acceso: str, refresco: str, usuario: User) -> None:
        self.acceso = acceso
        self.refresco = refresco
        self.usuario = usuario


def _sucursales_de(session: Session, usuario: User) -> tuple[UUID, list[UUID]]:
    """
    La sucursal activa y todas a las que el usuario alcanza.

    Si no tiene ninguna asignada se le da la que sea por defecto: un usuario sin
    sucursal no puede hacer nada, y bloquearle la entrada por un dato de
    configuracion que el no controla convierte un despiste del administrador en
    «el sistema no me deja trabajar».
    """
    asignaciones = session.exec(
        select(UserBranch)
        .where(UserBranch.user_id == usuario.id)
        .order_by(col(UserBranch.is_primary).desc())
    ).all()

    if asignaciones:
        return asignaciones[0].branch_id, [a.branch_id for a in asignaciones]

    predeterminada = session.exec(
        select(Branch)
        .where(col(Branch.is_active).is_(True))
        .order_by(col(Branch.is_default).desc(), col(Branch.sort_order))
    ).first()

    if predeterminada is None:
        raise ErrorAplicacion(
            409,
            "sin_sucursales",
            "No hay ninguna sucursal configurada. Crea una antes de entrar.",
        )

    return predeterminada.id, [predeterminada.id]


def _emitir(session: Session, usuario: User, metodo: MetodoDeAcceso) -> SesionEmitida:
    branch_id, branch_ids = _sucursales_de(session, usuario)

    acceso = firmar_acceso(
        {
            "sub": str(usuario.id),
            "tv": usuario.token_version,
            "name": usuario.name,
            "email": usuario.email,
            "branch_id": str(branch_id),
            "branch_ids": [str(b) for b in branch_ids],
            "permissions": [],
        },
        metodo,
    )

    refresco, jti, caducidad = firmar_refresco(usuario.id, metodo)
    session.add(
        RefreshToken(
            jti=jti,
            user_id=usuario.id,
            login_method=metodo,
            expires_at=caducidad,
        )
    )

    usuario.last_login_at = datetime.now(UTC)
    session.add(usuario)
    session.commit()

    _podar(session, usuario.id, conservar=jti)

    return SesionEmitida(acceso, refresco, usuario)


def _podar(session: Session, user_id: UUID, *, conservar: UUID) -> None:
    """
    Deja como mucho N refrescos vivos por usuario.

    Se poda DESPUES de guardar el nuevo y excluyendolo: podar antes, o sin la
    exclusion, haria que un inicio de sesion se invalidase a si mismo cuando el
    usuario ya tiene el tope.

    Va en `try` porque un fallo limpiando no puede impedir que alguien entre a
    trabajar: el tope es higiene, no seguridad.
    """
    try:
        vivos = session.exec(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(col(RefreshToken.revoked_at).is_(None))
            .where(RefreshToken.jti != conservar)
            .order_by(col(RefreshToken.created_at).desc())
        ).all()

        for sobrante in vivos[settings.max_refresh_por_usuario - 1 :]:
            sobrante.revoked_at = datetime.now(UTC)
            session.add(sobrante)
        session.commit()
    except Exception:
        session.rollback()


def entrar_por_correo(session: Session, email: str, password: str) -> SesionEmitida:
    usuario = session.exec(select(User).where(User.email == email.strip().lower())).first()

    # `verificar` gasta el mismo tiempo aunque no haya hash que comprobar, asi
    # que un correo inexistente y uno con contrasena mala tardan lo mismo.
    if usuario is None or not verificar(password, usuario.password_hash):
        raise ErrorAplicacion(401, "credenciales_invalidas", CREDENCIALES_INVALIDAS)

    if not usuario.is_active:
        raise ErrorAplicacion(401, "credenciales_invalidas", CREDENCIALES_INVALIDAS)

    return _emitir(session, usuario, "email")


def entrar_por_pin(session: Session, user_id: UUID, pin: str) -> SesionEmitida:
    usuario = session.get(User, user_id)

    if usuario is None or not verificar(pin, usuario.pin_hash) or not usuario.is_active:
        raise ErrorAplicacion(401, "pin_invalido", PIN_INVALIDO)

    return _emitir(session, usuario, "pin")


def renovar(session: Session, token: str) -> SesionEmitida:
    """
    Rotacion: el refresco usado se revoca y se emite uno nuevo.

    El metodo de acceso se PROPAGA del token viejo. Fijarlo a «correo» degradaria
    una sesion de PIN de cuatro horas a quince minutos, que es como un mesero
    acaba en el formulario de correo a media hora punta.
    """
    try:
        carga = leer_refresco(token)
    except jwt.PyJWTError as error:
        raise ErrorAplicacion(401, "refresco_invalido", "Hay que iniciar sesion.") from error

    jti = UUID(str(carga["jti"]))
    guardado = session.get(RefreshToken, jti)

    if guardado is None:
        raise ErrorAplicacion(401, "refresco_invalido", "Hay que iniciar sesion.")

    if not guardado.esta_vivo:
        # REUSO. Un refresco ya revocado que ademas tiene sucesor significa que
        # alguien esta reproduciendo un token viejo. No basta con rechazar este:
        # si un token antiguo circula, el actual tambien puede estarlo, asi que
        # se revoca la cadena entera y se sube el contador del usuario.
        if guardado.replaced_by is not None:
            _revocar_todo(session, guardado.user_id, subir_version=True)
        raise ErrorAplicacion(401, "refresco_invalido", "Hay que iniciar sesion.")

    usuario = session.get(User, guardado.user_id)
    if usuario is None or not usuario.is_active:
        raise ErrorAplicacion(401, "refresco_invalido", "Hay que iniciar sesion.")

    metodo: MetodoDeAcceso = "pin" if guardado.login_method == "pin" else "email"
    emitida = _emitir(session, usuario, metodo)

    guardado.revoked_at = datetime.now(UTC)
    nuevo = leer_refresco(emitida.refresco)
    guardado.replaced_by = UUID(str(nuevo["jti"]))
    session.add(guardado)
    session.commit()

    return emitida


def salir(session: Session, token: str | None) -> None:
    """Revoca el refresco de ESTA sesion. Las demas pantallas siguen abiertas."""
    if not token:
        return
    try:
        carga = leer_refresco(token)
    except jwt.PyJWTError:
        return

    guardado = session.get(RefreshToken, UUID(str(carga["jti"])))
    if guardado is not None and guardado.esta_vivo:
        guardado.revoked_at = datetime.now(UTC)
        session.add(guardado)
        session.commit()


def _revocar_todo(session: Session, user_id: UUID, *, subir_version: bool) -> None:
    from app.core import token_version

    vivos = session.exec(
        select(RefreshToken)
        .where(RefreshToken.user_id == user_id)
        .where(col(RefreshToken.revoked_at).is_(None))
    ).all()
    ahora = datetime.now(UTC)
    for vivo in vivos:
        vivo.revoked_at = ahora
        session.add(vivo)

    if subir_version and (usuario := session.get(User, user_id)) is not None:
        usuario.token_version += 1
        session.add(usuario)
        token_version.invalidar(user_id)

    session.commit()

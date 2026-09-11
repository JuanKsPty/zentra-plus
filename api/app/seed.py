"""
Siembra idempotente.

    python -m app.seed          lo imprescindible
    python -m app.seed --demo   ademas, datos de demostracion

Se corre en cada `pnpm run setup` y en el arranque de un entorno nuevo, asi que
tiene que poder ejecutarse N veces sin duplicar nada. La idempotencia va por
CLAVE NATURAL —el codigo de la sucursal, el correo del usuario— y nunca por
«¿hay filas?»: ese atajo hace que sembrar despues de borrar algo a mano no lo
restaure, que es justo cuando hace falta.
"""

import argparse
import logging
import secrets
import sys

from sqlmodel import Session, select

from app.core import permissions as P
from app.core.config import settings
from app.core.security import hashear
from app.db.session import engine
from app.models import Branch, BranchCounter, Permission, Role, RolePermission, User, UserBranch

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("zentra.seed")

CODIGO_SUCURSAL_PRINCIPAL = "PRIN"


def sembrar_sucursal_principal(session: Session) -> Branch:
    """
    La sucursal con la que arranca cualquier instalacion.

    Existe desde el primer dia aunque el negocio tenga un solo local: asi no hay
    dos caminos —«sin sucursal» y «con sucursal»— que mantener en cada consulta,
    y abrir la segunda sede es dar de alta una fila, no migrar el esquema.
    """
    sucursal = session.exec(select(Branch).where(Branch.code == CODIGO_SUCURSAL_PRINCIPAL)).first()

    if sucursal is None:
        sucursal = Branch(
            name="Principal",
            code=CODIGO_SUCURSAL_PRINCIPAL,
            timezone=settings.timezone,
            is_default=True,
            sort_order=0,
        )
        session.add(sucursal)
        session.commit()
        session.refresh(sucursal)
        logger.info("  + sucursal %s (%s)", sucursal.name, sucursal.code)
    else:
        logger.info("  = sucursal %s (%s)", sucursal.name, sucursal.code)

    asegurar_contador(session, sucursal)
    return sucursal


def asegurar_contador(session: Session, sucursal: Branch) -> None:
    """
    La fila contador de una sucursal.

    Se siembra aqui y tambien al dar de alta una sucursal. Que este en los dos
    sitios no es duplicacion: una sucursal sin contador no puede recibir
    comandas, y descubrirlo a media hora punta es lo que hay que evitar.
    """
    if session.get(BranchCounter, sucursal.id) is None:
        session.add(BranchCounter(branch_id=sucursal.id))
        session.commit()
        logger.info("  + contador de cuentas para %s", sucursal.code)


def sembrar_permisos(session: Session) -> None:
    """
    Materializa el catalogo de constantes en la tabla.

    La fuente de verdad es `app/core/permissions.py`: la tabla existe para que la
    pantalla de roles pueda listarlos y para que la relacion con los roles sea
    una clave foranea de verdad. Un permiso nuevo en el codigo aparece en la base
    al sembrar, sin migracion.
    """
    existentes = {p.key for p in session.exec(select(Permission)).all()}
    nuevos = 0
    for clave in P.TODOS:
        if clave in existentes:
            continue
        modulo, accion = P.partir(clave)
        session.add(Permission(key=clave, module=modulo, action=accion))
        nuevos += 1
    session.commit()
    logger.info("  %s %d permisos", "+" if nuevos else "=", nuevos or len(P.TODOS))


def sembrar_roles(session: Session) -> Role:
    """
    Los roles de sistema, con sus permisos REESCRITOS en cada siembra.

    Reescribirlos es lo que hace que anadir un permiso a «Cajero» en el codigo
    llegue a la base sin migracion. Lo que NO se toca es el nombre ni la
    existencia: `is_system` los protege del borrado, porque si alguien borra
    «Cajero», quien lo tenia se queda sin poder cobrar.
    """
    administrador: Role | None = None

    for nombre, (descripcion, claves) in P.ROLES_DE_SISTEMA.items():
        rol = session.exec(select(Role).where(Role.name == nombre)).first()
        if rol is None:
            rol = Role(name=nombre, description=descripcion, is_system=True)
            session.add(rol)
            session.commit()
            session.refresh(rol)
            logger.info("  + rol %s", nombre)
        else:
            rol.description = descripcion
            rol.is_system = True
            session.add(rol)
            session.commit()

        actuales = {
            f.permission_key
            for f in session.exec(
                select(RolePermission).where(RolePermission.role_id == rol.id)
            ).all()
        }
        deseados = set(claves)

        for clave in deseados - actuales:
            session.add(RolePermission(role_id=rol.id, permission_key=clave))
        for clave in actuales - deseados:
            sobra = session.get(RolePermission, (rol.id, clave))
            if sobra is not None:
                session.delete(sobra)
        session.commit()

        if nombre == P.ADMINISTRADOR:
            administrador = rol

    assert administrador is not None
    return administrador


def sembrar_admin(session: Session, sucursal: Branch, rol: Role) -> None:
    """
    El primer usuario, el unico que puede crear a los demas.

    Las credenciales salen de SEED_ADMIN_EMAIL y SEED_ADMIN_PASSWORD. Fuera de
    desarrollo, si faltan NO SE CREA NADA y se dice por que: un administrador
    con credenciales que estan escritas en un repositorio publico es peor que no
    tener administrador.

    En desarrollo, si falta la contrasena se genera una al azar y se imprime UNA
    VEZ. Cambia en cada instalacion nueva, asi que no hay nada que publicar, y
    sigue siendo un comando y a trabajar.
    """
    correo = settings.seed_admin_email.strip().lower()

    if not correo:
        if not settings.is_dev:
            logger.warning("  ! sin administrador: define SEED_ADMIN_EMAIL y SEED_ADMIN_PASSWORD")
            return
        correo = "admin@zentra.local"

    existente = session.exec(select(User).where(User.email == correo)).first()
    if existente is not None:
        # NUNCA se reescribe la contrasena de un admin que ya existe: sembrar
        # otra vez no puede devolver el acceso a quien lo perdio.
        logger.info("  = administrador %s", correo)
        if existente.role_id is None:
            existente.role_id = rol.id
            session.add(existente)
            session.commit()
        asegurar_asignacion(session, existente, sucursal)
        return

    clave = settings.seed_admin_password.strip()
    generada = False
    if not clave:
        if not settings.is_dev:
            logger.warning("  ! sin administrador: falta SEED_ADMIN_PASSWORD")
            return
        clave = secrets.token_urlsafe(12)
        generada = True

    admin = User(
        name=settings.seed_admin_name,
        email=correo,
        password_hash=hashear(clave),
        role_id=rol.id,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    asegurar_asignacion(session, admin, sucursal)

    logger.info("  + administrador %s", correo)
    if generada:
        logger.warning("    contrasena generada (se muestra una sola vez): %s", clave)


def asegurar_asignacion(session: Session, usuario: User, sucursal: Branch) -> None:
    ya = session.get(UserBranch, (usuario.id, sucursal.id))
    if ya is None:
        session.add(UserBranch(user_id=usuario.id, branch_id=sucursal.id, is_primary=True))
        session.commit()


def sembrar(*, demo: bool = False) -> None:
    logger.info("Sembrando sobre %s", settings.database_kind)
    with Session(engine) as session:
        sembrar_permisos(session)
        rol_admin = sembrar_roles(session)
        sucursal = sembrar_sucursal_principal(session)
        sembrar_admin(session, sucursal, rol_admin)
    if demo:
        logger.info("  (todavia no hay datos de demostracion que sembrar)")
    logger.info("Listo.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Siembra de Zentra+")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="ademas de lo imprescindible, carga datos de demostracion",
    )
    argumentos = parser.parse_args()
    sembrar(demo=argumentos.demo)
    return 0


if __name__ == "__main__":
    sys.exit(main())

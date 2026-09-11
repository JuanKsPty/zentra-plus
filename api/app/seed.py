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
import sys

from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import engine
from app.models import Branch, BranchCounter

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


def sembrar(*, demo: bool = False) -> None:
    logger.info("Sembrando sobre %s", settings.database_kind)
    with Session(engine) as session:
        sembrar_sucursal_principal(session)
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

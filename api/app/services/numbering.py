"""
El numero de cuenta, uno por sucursal.
"""

from uuid import UUID

from sqlalchemy import Uuid, bindparam, text
from sqlmodel import Session


def siguiente_numero(session: Session, branch_id: UUID) -> int:
    """
    `UPDATE ... RETURNING` sobre la fila contador de la sucursal.

    ES ATOMICO E IMPOSIBLE DE REPETIR. PostgreSQL toma el cerrojo de esa fila y
    la segunda peticion ESPERA al commit de la primera: no falla, espera. Y a
    diferencia de una secuencia, el numero se devuelve si la transaccion aborta,
    asi que no deja huecos — que importa porque un cajero que ve saltar los
    numeros pregunta que paso con los que faltan.

    Lo que NO se hace nunca es `MAX(order_number) + 1`: dos lecturas ven el
    mismo maximo y entregan el mismo numero, y con reintentos los reintentos
    vuelven a chocar entre si.

    Se llama LO MAS TARDE POSIBLE dentro de la transaccion: el cerrojo dura
    hasta el commit, asi que pedir el numero antes de validar el catalogo
    encolaria a todas las comandas de esa sucursal mientras tanto.
    """
    # El parametro se ata CON SU TIPO. Pasarlo como cadena lo manda a PostgreSQL
    # como varchar, y ahi `uuid = varchar` no es un operador que exista: la
    # consulta revienta con «operator does not exist», que no se parece en nada
    # a lo que esta mal.
    sucursal = bindparam("sucursal", branch_id, type_=Uuid)

    fila = session.exec(
        text(
            "UPDATE branch_counters SET last_order_number = last_order_number + 1 "
            "WHERE branch_id = :sucursal RETURNING last_order_number"
        ).bindparams(sucursal)
    ).first()

    if fila is None:
        # Una sucursal sin contador no puede recibir comandas, y descubrirlo a
        # media hora punta es lo que hay que evitar. Se siembra al vuelo.
        #
        # Por el ORM y no con SQL crudo: este camino se recorre una vez en la
        # vida de una sucursal, asi que no hay nada que optimizar, y el ORM sabe
        # solo que `branch_id` es un uuid. Con SQL crudo hay que decirselo, y
        # equivocarse ahi da un «column is of type uuid but expression is of
        # type character varying» que no se parece a lo que esta mal.
        from app.models import BranchCounter

        session.add(BranchCounter(branch_id=branch_id, last_order_number=1))
        session.flush()
        return 1

    return int(fila[0])

"""
El alcance de sucursal de una peticion, y el unico sitio por el que se consulta
una tabla que lo tenga.

LA REGLA

    `None` nunca significa «sin filtro».

Un alcance siempre trae una sucursal concreta, salvo que alguien haya pedido el
consolidado a proposito y tenga permiso. Asi, olvidarse del filtro deja de ser
una fuga de datos entre sedes para ser algo que no se puede ni escribir: la
funcion exige el alcance como argumento.
"""

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.core.errors import ErrorAplicacion
from app.models.base import ConSucursal


@dataclass(frozen=True)
class Alcance:
    """
    Sobre que sucursales opera esta peticion.

    `branch_id is None` significa CONSOLIDADO —todas las que la sesion alcanza—
    y solo se llega ahi pidiendolo. Nunca es el valor por defecto.
    """

    branch_id: UUID | None
    # Todas a las que la sesion tiene acceso. En el consolidado es el filtro.
    branch_ids: tuple[UUID, ...] = ()

    @property
    def consolidado(self) -> bool:
        return self.branch_id is None

    @classmethod
    def de(cls, branch_id: UUID) -> "Alcance":
        """Una sola sucursal. Es el caso normal y el que se usa en las pruebas."""
        return cls(branch_id=branch_id, branch_ids=(branch_id,))


def consulta[T](modelo: type[T], alcance: Alcance) -> SelectOfScalar[T]:
    """
    El unico constructor de consultas para tablas con sucursal.

    Exige el alcance como argumento: no hay forma de escribir la llamada sin
    decidir conscientemente el ambito. Una tabla que no es de sucursal —el
    catalogo, los roles— pasa sin filtro, que es lo correcto: el menu se define
    una vez para todo el negocio.
    """
    q = select(modelo)

    if not (isinstance(modelo, type) and issubclass(modelo, ConSucursal)):
        return q

    if alcance.consolidado:
        # Ni siquiera el consolidado es «todo»: es todo lo que ESTA SESION
        # alcanza. Un gerente de dos sedes no ve la tercera.
        if not alcance.branch_ids:
            raise ErrorAplicacion(
                403,
                "sin_sucursales",
                "Tu usuario no tiene ninguna sucursal asignada.",
            )
        return q.where(col(modelo.branch_id).in_(alcance.branch_ids))

    return q.where(col(modelo.branch_id) == alcance.branch_id)


def fijar_sucursal[T](instancia: T, alcance: Alcance) -> T:
    """
    Pone la sucursal en algo que se va a guardar.

    La sucursal se toma del alcance y NUNCA del cuerpo de la peticion: los
    esquemas de entrada no declaran `branch_id`, y con `extra="forbid"` mandarlo
    devuelve 422. Si viniera de fuera, escribir en la sucursal de al lado seria
    cuestion de cambiar un campo del JSON.
    """
    if alcance.consolidado:
        # No existe «crear una comanda en todas las sucursales». Si esto salta,
        # es que un endpoint de escritura acepto ?branch=all, que no debe.
        raise ErrorAplicacion(
            400,
            "escritura_sin_sucursal",
            "Hay que elegir una sucursal para poder guardar.",
        )
    if isinstance(instancia, ConSucursal):
        instancia.branch_id = alcance.branch_id  # type: ignore[assignment]
    return instancia

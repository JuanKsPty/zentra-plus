"""
La forma de un listado, decidida antes del primer listado.

Una sola convencion: `page`/`size` a la entrada, `{items, page, size, total,
has_more}` a la salida. Se elige sobre `take`/`skip` por dos motivos concretos:
se traduce a un paginador de interfaz sin aritmetica en el cliente, y no admite
estados que ninguna pantalla produce (un `skip=37` con `take=50` es valido y no
significa nada).

Va aqui y no cuando haya seis listados porque anadir paginacion despues no es
cambiar un endpoint: es cambiar la FORMA de la respuesta de lista a objeto, lo
que rompe a la vez cada servicio, cada hook y cada prueba del frontend.
"""

from typing import Annotated

from fastapi import Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

# Tope duro. No es una sugerencia: sin el, el dia que haya cuatro mil comandas
# alguien pide la lista entera desde una tableta y se queda sin memoria.
TAMANO_MAXIMO = 200
TAMANO_POR_DEFECTO = 50


class ParametrosPagina(BaseModel):
    page: int = Field(default=1, ge=1)
    size: int = Field(default=TAMANO_POR_DEFECTO, ge=1, le=TAMANO_MAXIMO)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size


def paginacion(
    page: Annotated[int, Query(ge=1, description="Pagina, empezando en 1")] = 1,
    size: Annotated[
        int,
        Query(ge=1, le=TAMANO_MAXIMO, description=f"Elementos por pagina (maximo {TAMANO_MAXIMO})"),
    ] = TAMANO_POR_DEFECTO,
) -> ParametrosPagina:
    return ParametrosPagina(page=page, size=size)


Paginacion = Annotated[ParametrosPagina, Depends(paginacion)]


class Pagina[T](BaseModel):
    items: list[T]
    page: int
    size: int
    # El total es una consulta extra, y se paga a proposito: es lo que permite
    # que una pantalla diga «mostrando 50 de 312» en vez de cortar en silencio.
    # Un tope silencioso se lee como «esto es todo», que es una forma de mentir.
    total: int
    has_more: bool


def paginar[T](
    session: Session,
    consulta: SelectOfScalar[T],
    parametros: ParametrosPagina,
) -> Pagina[T]:
    """
    Ejecuta la consulta paginada y cuenta el total con el mismo filtro.

    El COUNT se arma desde la subconsulta y no repitiendo el WHERE a mano: asi
    no pueden divergir, que es como acaba una pantalla diciendo «312 resultados»
    y ensenando otros.
    """
    total = session.exec(select(func.count()).select_from(consulta.order_by(None).subquery())).one()

    items = session.exec(consulta.offset(parametros.offset).limit(parametros.size)).all()

    return Pagina(
        items=list(items),
        page=parametros.page,
        size=parametros.size,
        total=total,
        has_more=parametros.offset + len(items) < total,
    )

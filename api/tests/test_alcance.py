from uuid import UUID, uuid4

import pytest
from sqlmodel import Field, Session, SQLModel, select

from app.core.errors import ErrorAplicacion
from app.db.scoping import Alcance, consulta, fijar_sucursal
from app.models.base import ConSucursal

SEDE_A = UUID("11111111-1111-4111-8111-111111111111")
SEDE_B = UUID("22222222-2222-4222-8222-222222222222")


class Comanda(ConSucursal, SQLModel, table=True):
    """Una tabla de la operacion: existe dentro de una sucursal."""

    __tablename__ = "comandas_de_prueba"
    id: int | None = Field(default=None, primary_key=True)
    etiqueta: str


class Producto(SQLModel, table=True):
    """Catalogo: es del negocio entero y NO lleva sucursal."""

    __tablename__ = "productos_de_prueba"
    id: int | None = Field(default=None, primary_key=True)
    nombre: str


@pytest.fixture(name="con_datos")
def con_datos_fixture(session: Session) -> Session:
    SQLModel.metadata.create_all(session.get_bind())
    session.add(Comanda(branch_id=SEDE_A, etiqueta="mesa 1 de A"))
    session.add(Comanda(branch_id=SEDE_A, etiqueta="mesa 2 de A"))
    session.add(Comanda(branch_id=SEDE_B, etiqueta="mesa 1 de B"))
    session.add(Producto(nombre="empanada"))
    session.commit()
    return session


def test_una_sucursal_solo_ve_lo_suyo(con_datos: Session) -> None:
    etiquetas = [c.etiqueta for c in con_datos.exec(consulta(Comanda, Alcance.de(SEDE_A))).all()]

    assert etiquetas == ["mesa 1 de A", "mesa 2 de A"]


def test_el_catalogo_no_se_filtra(con_datos: Session) -> None:
    """
    Es la mitad del modelo: el menu se define una vez para todo el negocio.

    Si `consulta()` filtrara todo por sucursal, cada sede necesitaria su propio
    catalogo y comparar el ticket promedio de un producto entre locales
    requeriria una tabla de equivalencias.
    """
    nombres = [p.nombre for p in con_datos.exec(consulta(Producto, Alcance.de(SEDE_A))).all()]

    assert nombres == ["empanada"]


def test_el_consolidado_es_lo_que_ESTA_SESION_alcanza(con_datos: Session) -> None:
    """Ni siquiera «todas» es todo: un gerente de dos sedes no ve la tercera."""
    alcance = Alcance(branch_id=None, branch_ids=(SEDE_A,))

    etiquetas = [c.etiqueta for c in con_datos.exec(consulta(Comanda, alcance)).all()]

    assert etiquetas == ["mesa 1 de A", "mesa 2 de A"]


def test_un_consolidado_sin_sucursales_no_devuelve_todo(con_datos: Session) -> None:
    """
    El caso que separa «consolidado» de «me olvide del filtro».

    Si una lista de sucursales vacia significara «sin WHERE», un usuario mal
    configurado veria el negocio entero. Es un 403, no una consulta sin filtro.
    """
    with pytest.raises(ErrorAplicacion) as excinfo:
        con_datos.exec(consulta(Comanda, Alcance(branch_id=None, branch_ids=())))

    assert excinfo.value.status_code == 403


def test_la_sucursal_de_lo_que_se_guarda_sale_del_alcance() -> None:
    comanda = fijar_sucursal(Comanda(branch_id=uuid4(), etiqueta="x"), Alcance.de(SEDE_B))

    assert comanda.branch_id == SEDE_B


def test_no_se_puede_guardar_en_el_consolidado() -> None:
    """No existe «crear una comanda en todas las sucursales»."""
    with pytest.raises(ErrorAplicacion) as excinfo:
        fijar_sucursal(
            Comanda(branch_id=SEDE_A, etiqueta="x"),
            Alcance(branch_id=None, branch_ids=(SEDE_A, SEDE_B)),
        )

    assert excinfo.value.status_code == 400


def test_una_consulta_a_pelo_si_cruza_sucursales(con_datos: Session) -> None:
    """
    La prueba que justifica que exista `consulta()`.

    Un `select(Comanda)` normal devuelve las tres, incluida la de la otra sede.
    No es un fallo de SQLModel: es lo que pasa cuando el filtro depende de que
    alguien se acuerde. Por eso hay un unico constructor que lo exige, y por eso
    `test_sin_consultas_a_pelo` vigila que nadie lo esquive.
    """
    assert len(con_datos.exec(select(Comanda)).all()) == 3

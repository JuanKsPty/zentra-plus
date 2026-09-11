from typing import Annotated

import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlmodel import Field, Session, SQLModel, select

from app.core.pagination import TAMANO_MAXIMO, Pagina, Paginacion, ParametrosPagina, paginar
from app.db.session import get_session
from app.main import app


class Cosa(SQLModel, table=True):
    __tablename__ = "cosas_de_prueba"
    id: int | None = Field(default=None, primary_key=True)
    nombre: str


_pruebas = APIRouter(prefix="/_pruebas", include_in_schema=False)


@_pruebas.get("/cosas")
def _listar(
    pagina: Paginacion,
    session: Annotated[Session, Depends(get_session)],
) -> Pagina[Cosa]:
    return paginar(session, select(Cosa).order_by(Cosa.id), pagina)


app.include_router(_pruebas, prefix="/api")


@pytest.fixture(name="con_cosas")
def con_cosas_fixture(session: Session) -> Session:
    SQLModel.metadata.create_all(session.get_bind())
    for numero in range(1, 13):
        session.add(Cosa(nombre=f"cosa {numero}"))
    session.commit()
    return session


def test_la_primera_pagina_trae_el_total_y_avisa_de_que_hay_mas(
    client: TestClient, con_cosas: Session
) -> None:
    cuerpo = client.get("/api/_pruebas/cosas?page=1&size=5").json()

    assert [c["nombre"] for c in cuerpo["items"]] == [f"cosa {n}" for n in range(1, 6)]
    assert cuerpo["page"] == 1
    assert cuerpo["size"] == 5
    # El total es lo que permite a una pantalla decir «mostrando 5 de 12» en vez
    # de cortar en silencio, que se lee como «esto es todo».
    assert cuerpo["total"] == 12
    assert cuerpo["has_more"] is True


def test_la_ultima_pagina_no_dice_que_haya_mas(client: TestClient, con_cosas: Session) -> None:
    cuerpo = client.get("/api/_pruebas/cosas?page=3&size=5").json()

    assert len(cuerpo["items"]) == 2
    assert cuerpo["has_more"] is False


def test_una_pagina_vacia_no_es_un_error(client: TestClient, con_cosas: Session) -> None:
    cuerpo = client.get("/api/_pruebas/cosas?page=99&size=5").json()

    assert cuerpo["items"] == []
    assert cuerpo["total"] == 12
    assert cuerpo["has_more"] is False


def test_el_tope_es_duro(client: TestClient, con_cosas: Session) -> None:
    """
    Pedir mas del maximo es un 422, no un recorte silencioso.

    Recortar sin avisar deja al cliente creyendo que pidio 500 y recibio todo lo
    que hay; el 422 le dice que su peticion era la equivocada.
    """
    respuesta = client.get(f"/api/_pruebas/cosas?size={TAMANO_MAXIMO + 1}")

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["code"] == "datos_invalidos"
    assert respuesta.json()["error"]["details"][0]["field"] == "size"


def test_la_pagina_cero_no_existe(client: TestClient, con_cosas: Session) -> None:
    assert client.get("/api/_pruebas/cosas?page=0").status_code == 422


def test_el_offset_se_calcula_desde_la_pagina_uno() -> None:
    assert ParametrosPagina(page=1, size=50).offset == 0
    assert ParametrosPagina(page=2, size=50).offset == 50
    assert ParametrosPagina(page=4, size=25).offset == 75

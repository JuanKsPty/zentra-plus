from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import permissions as P
from app.models import Branch, Category, Product, ProductBranch
from tests.factories import cookie_con, crear_sucursal

LECTOR = [P.CATALOG_READ]
ESCRITOR = [P.CATALOG_READ, P.CATALOG_WRITE]


@pytest.fixture(name="sedes")
def sedes_fixture(session: Session) -> tuple[Branch, Branch]:
    return crear_sucursal(session), crear_sucursal(session, code="NOR", name="Norte")


@pytest.fixture(name="empanada")
def empanada_fixture(session: Session) -> Product:
    categoria = Category(name="Entradas")
    session.add(categoria)
    session.commit()
    session.refresh(categoria)

    producto = Product(name="Empanada", price=Decimal("2.50"), category_id=categoria.id)
    session.add(producto)
    session.commit()
    session.refresh(producto)
    return producto


def test_la_carta_es_la_misma_en_las_dos_sedes(
    client: TestClient, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    """
    La mitad del modelo multisucursal.

    El catalogo se define UNA vez para todo el negocio. Si cada sede tuviera el
    suyo, comparar el ticket promedio de un producto entre locales necesitaria
    una tabla de equivalencias, y el dueno no podria decir «la empanada se vende
    mejor en el norte» sin montarla.
    """
    principal, norte = sedes

    for sede in (principal, norte):
        client.cookies.update(cookie_con(LECTOR, branch_id=sede.id))
        cuerpo = client.get("/api/catalog/products").json()
        assert [p["name"] for p in cuerpo["items"]] == ["Empanada"]


def test_sin_override_el_precio_se_hereda(
    client: TestClient, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    """
    Ausencia de fila = herencia.

    Es lo que evita sembrar N x M filas al dar de alta una sucursal: con cuatro
    sedes y trescientos productos serian mil doscientas filas que solo repiten
    el precio base.
    """
    principal, _ = sedes
    client.cookies.update(cookie_con(LECTOR, branch_id=principal.id))

    producto = client.get("/api/catalog/products").json()["items"][0]

    assert Decimal(str(producto["effective_price"])) == Decimal("2.50")
    assert producto["is_available"] is True


def test_el_precio_de_una_sede_no_toca_a_la_otra(
    client: TestClient, session: Session, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    principal, norte = sedes

    client.cookies.update(cookie_con(ESCRITOR, branch_id=norte.id))
    puesto = client.put(
        f"/api/catalog/products/{empanada.id}/branch", json={"price": "3.25"}
    ).json()
    assert Decimal(str(puesto["effective_price"])) == Decimal("3.25")

    client.cookies.update(cookie_con(LECTOR, branch_id=principal.id))
    otra = client.get("/api/catalog/products").json()["items"][0]
    assert Decimal(str(otra["effective_price"])) == Decimal("2.50")


def test_cambiar_el_precio_base_llega_a_quien_no_lo_habia_pisado(
    client: TestClient, session: Session, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    """
    Por esto el override NO copia el precio base al crearse.

    Si al marcar «agotado» se copiara el precio, esa sede dejaria de recibir las
    subidas del negocio para siempre — y nadie lo relacionaria con haber tocado
    un interruptor de disponibilidad meses antes.
    """
    principal, norte = sedes

    # El norte solo dice «hoy no queda». No toca el precio.
    client.cookies.update(cookie_con(ESCRITOR, branch_id=norte.id))
    client.put(f"/api/catalog/products/{empanada.id}/branch", json={"is_available": False})

    # El negocio sube el precio.
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    client.patch(f"/api/catalog/products/{empanada.id}", json={"price": "2.75"})

    client.cookies.update(cookie_con(LECTOR, branch_id=norte.id))
    en_norte = client.get("/api/catalog/products").json()["items"][0]

    assert Decimal(str(en_norte["effective_price"])) == Decimal("2.75")
    assert en_norte["is_available"] is False


def test_un_producto_sin_override_no_desaparece_de_la_sede(
    client: TestClient, session: Session, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    """
    El JOIN tiene que ser LEFT.

    Con un join normal, un producto sin override desapareceria del catalogo de
    esa sede, y el sintoma seria «faltan productos en la sucursal nueva» — que
    nadie relaciona con el tipo de join.
    """
    principal, norte = sedes

    session.add(
        ProductBranch(product_id=empanada.id, branch_id=principal.id, price=Decimal("9.99"))
    )
    session.commit()

    client.cookies.update(cookie_con(LECTOR, branch_id=norte.id))
    items = client.get("/api/catalog/products").json()["items"]

    assert len(items) == 1
    assert Decimal(str(items[0]["effective_price"])) == Decimal("2.50")


def test_retirar_es_baja_logica(
    client: TestClient, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    """
    Un DELETE de verdad convierte en basura toda cuenta historica que lo
    referencia, y los reportes empiezan a fallar con claves rotas meses despues.
    """
    principal, _ = sedes
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))

    retirado = client.delete(f"/api/catalog/products/{empanada.id}").json()
    assert retirado["is_active"] is False

    assert client.get("/api/catalog/products").json()["items"] == []
    con_inactivos = client.get("/api/catalog/products?incluir_inactivos=true").json()
    assert len(con_inactivos["items"]) == 1


def test_leer_no_basta_para_escribir(
    client: TestClient, sedes: tuple[Branch, Branch], empanada: Product
) -> None:
    principal, _ = sedes
    client.cookies.update(cookie_con(LECTOR, branch_id=principal.id))

    assert (
        client.patch(f"/api/catalog/products/{empanada.id}", json={"price": "1"}).status_code == 403
    )
    assert client.post("/api/catalog/categories", json={"name": "Postres"}).status_code == 403


def test_una_estacion_inventada_se_rechaza(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """La estacion decide en que tablero aparece la linea; una que no existe la
    haria invisible para cocina y para barra."""
    principal, _ = sedes
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))

    respuesta = client.post(
        "/api/catalog/products",
        json={"name": "Cafe", "price": "1.50", "station": "terraza"},
    )

    assert respuesta.status_code == 404
    assert uuid4() is not None

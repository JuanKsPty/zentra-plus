from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import permissions as P
from app.models import BusinessConfig
from tests.factories import cookie_con


@pytest.fixture(name="configurado")
def configurado_fixture(session: Session) -> BusinessConfig:
    fila = BusinessConfig(business_name="Cafe Zentra", currency="PAB", tax_rate=Decimal("0.07"))
    session.add(fila)
    session.commit()
    session.refresh(fila)
    return fila


def test_leer_pide_settings_read(client: TestClient, configurado: BusinessConfig) -> None:
    client.cookies.update(cookie_con([]))
    assert client.get("/api/business-config").status_code == 403

    client.cookies.update(cookie_con([P.SETTINGS_READ]))
    cuerpo = client.get("/api/business-config").json()
    assert cuerpo["business_name"] == "Cafe Zentra"
    assert cuerpo["currency"] == "PAB"


def test_leer_no_basta_para_escribir(client: TestClient, configurado: BusinessConfig) -> None:
    """Un cajero tiene `settings:read` para imprimir el recibo; no para cambiar el impuesto."""
    client.cookies.update(cookie_con([P.SETTINGS_READ]))

    respuesta = client.put("/api/business-config", json={"business_name": "Otro"})

    assert respuesta.status_code == 403


def test_actualizar_solo_toca_lo_que_vino(client: TestClient, configurado: BusinessConfig) -> None:
    """
    Sin `exclude_unset`, un formulario que manda tres campos borraria los otros
    cuatro poniendolos a null, y el sintoma seria «se borro el pie del recibo».
    """
    client.cookies.update(cookie_con([P.SETTINGS_READ, P.SETTINGS_WRITE]))

    cuerpo = client.put("/api/business-config", json={"business_name": "Zentra Centro"}).json()

    assert cuerpo["business_name"] == "Zentra Centro"
    assert cuerpo["currency"] == "PAB"
    assert Decimal(str(cuerpo["tax_rate"])) == Decimal("0.07")


def test_un_impuesto_imposible_se_rechaza(client: TestClient, configurado: BusinessConfig) -> None:
    client.cookies.update(cookie_con([P.SETTINGS_READ, P.SETTINGS_WRITE]))

    respuesta = client.put("/api/business-config", json={"tax_rate": "1.5"})

    assert respuesta.status_code == 422
    assert respuesta.json()["error"]["details"][0]["field"] == "tax_rate"


def test_sin_sembrar_lo_dice_con_palabras(client: TestClient) -> None:
    """
    Un 500 aqui haria buscar un endpoint roto. El problema es que nadie sembro,
    y decirlo ahorra media hora.
    """
    client.cookies.update(cookie_con([P.SETTINGS_READ]))

    respuesta = client.get("/api/business-config")

    assert respuesta.status_code == 409
    assert respuesta.json()["error"]["code"] == "sin_configuracion"

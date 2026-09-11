from fastapi import APIRouter
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.core.errors import Conflicto, ErrorAplicacion
from app.main import app

# Rutas de prueba, montadas una sola vez sobre la app real: asi se comprueban
# los manejadores de verdad y no una copia del arnes.
_pruebas = APIRouter(prefix="/_pruebas", include_in_schema=False)


class Cuerpo(BaseModel):
    nombre: str = Field(min_length=3)
    cantidad: int = Field(gt=0)


@_pruebas.post("/validar")
def _validar(cuerpo: Cuerpo) -> dict:
    return {"ok": True, "nombre": cuerpo.nombre}


@_pruebas.get("/negocio")
def _negocio() -> dict:
    raise Conflicto("saldo_pendiente", "La cuenta tiene 45.00 sin cobrar.")


@_pruebas.get("/roto")
def _roto() -> dict:
    raise RuntimeError("parametros: ('juan@ejemplo.com', '$argon2id$v=19$secreto')")


@_pruebas.get("/perdido")
def _perdido() -> dict:
    raise ErrorAplicacion(404, "no_encontrado", "No existe esa mesa.")


app.include_router(_pruebas, prefix="/api")


def test_un_error_de_negocio_lleva_codigo_y_mensaje(client: TestClient) -> None:
    respuesta = client.get("/api/_pruebas/negocio")

    assert respuesta.status_code == 409
    error = respuesta.json()["error"]
    assert error["code"] == "saldo_pendiente"
    assert "45.00" in error["message"]
    assert error["details"] == []
    # Reservado aunque todavia no se rellene: la forma no puede cambiar despues.
    assert "request_id" in error


def test_los_errores_de_validacion_salen_campo_a_campo(client: TestClient) -> None:
    """
    El 422 de Pydantic tiene que llegar con la forma de la casa.

    Si se dejara pasar el `detail` de FastAPI tal cual, el cuerpo seria una
    lista de objetos con `loc`, `msg` y `type`, y cada formulario tendria que
    inventarse como leerla. Es el error mas frecuente de todos, asi que es el
    que mas barato sale unificar.
    """
    respuesta = client.post("/api/_pruebas/validar", json={"nombre": "ab", "cantidad": 0})

    assert respuesta.status_code == 422
    error = respuesta.json()["error"]
    assert error["code"] == "datos_invalidos"

    por_campo = {d["field"]: d["message"] for d in error["details"]}
    assert set(por_campo) == {"nombre", "cantidad"}
    # Y en espanol: el mensaje de error es interfaz, no un detalle tecnico.
    assert por_campo["nombre"] == "Es demasiado corto."
    assert por_campo["cantidad"] == "Tiene que ser mayor."


def test_un_campo_que_falta_se_nombra(client: TestClient) -> None:
    respuesta = client.post("/api/_pruebas/validar", json={})

    detalles = {d["field"]: d["message"] for d in respuesta.json()["error"]["details"]}
    assert detalles == {"nombre": "Hace falta este dato.", "cantidad": "Hace falta este dato."}


def test_un_error_no_previsto_no_filtra_nada(client_sin_relanzar: TestClient) -> None:
    """
    Lo importante no es que devuelva 500, es QUE NO CUENTA.

    `str()` de una excepcion de SQLAlchemy incluye los parametros enlazados de
    la consulta, asi que un insert fallido en la tabla de usuarios pondria un
    hash de credencial en la respuesta. Aqui se simula exactamente eso.
    """
    respuesta = client_sin_relanzar.get("/api/_pruebas/roto")

    assert respuesta.status_code == 500
    cuerpo = respuesta.text
    assert "argon2" not in cuerpo
    assert "ejemplo.com" not in cuerpo
    assert respuesta.json()["error"] == {
        "code": "error_interno",
        "message": "Error interno del servidor.",
        "details": [],
        "request_id": None,
    }


def test_una_ruta_que_no_existe_tambien_lleva_el_sobre(client: TestClient) -> None:
    respuesta = client.get("/api/no-existe-esta-ruta")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "no_encontrado"


def test_no_encontrado_de_negocio(client: TestClient) -> None:
    respuesta = client.get("/api/_pruebas/perdido")

    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["message"] == "No existe esa mesa."

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core import permissions as P
from app.models import Branch
from tests.factories import cookie_con, crear_sucursal

LECTOR = [P.FLOOR_READ]
ESCRITOR = [P.FLOOR_READ, P.FLOOR_WRITE]


@pytest.fixture(name="sedes")
def sedes_fixture(session: Session) -> tuple[Branch, Branch]:
    return crear_sucursal(session), crear_sucursal(session, code="NOR", name="Norte")


def _zona(client: TestClient, sede: Branch, nombre: str = "Terraza") -> str:
    client.cookies.update(cookie_con(ESCRITOR, branch_id=sede.id))
    return client.post("/api/floor/sectors", json={"name": nombre}).json()["id"]


def test_las_dos_sedes_pueden_tener_una_terraza(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """«Terraza» puede existir en las dos. Lo que no puede haber son dos en la misma."""
    principal, norte = sedes

    assert _zona(client, principal) != _zona(client, norte)

    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    repetida = client.post("/api/floor/sectors", json={"name": "Terraza"})

    assert repetida.status_code == 409
    assert repetida.json()["error"]["code"] == "zona_repetida"


def test_las_dos_sedes_pueden_tener_una_mesa_1(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """
    En LoklFlow el numero era unico GLOBAL, asi que la segunda sede no podia
    tener una «mesa 1». Operativamente es absurdo: cada local numera desde uno.
    """
    principal, norte = sedes

    for sede in (principal, norte):
        zona = _zona(client, sede, "Interior")
        client.cookies.update(cookie_con(ESCRITOR, branch_id=sede.id))
        creada = client.post("/api/floor/tables", json={"number": 1, "sector_id": zona})
        assert creada.status_code == 201, creada.text


def test_dos_mesas_con_el_mismo_numero_en_la_misma_sede_chocan(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """
    Y el choque sale como error de negocio, no como 500.

    La comprobacion previa seria un leer-antes-de-escribir con una ventana
    abierta entre las dos; el indice unico la cierra y el servicio traduce la
    violacion al mismo mensaje.
    """
    principal, _ = sedes
    zona = _zona(client, principal, "Interior")

    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    client.post("/api/floor/tables", json={"number": 7, "sector_id": zona})
    repetida = client.post("/api/floor/tables", json={"number": 7, "sector_id": zona})

    assert repetida.status_code == 409
    assert repetida.json()["error"]["code"] == "mesa_repetida"


def test_una_sede_no_ve_las_mesas_de_la_otra(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    principal, norte = sedes
    zona = _zona(client, principal, "Interior")
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    client.post("/api/floor/tables", json={"number": 3, "sector_id": zona})

    client.cookies.update(cookie_con(LECTOR, branch_id=norte.id))

    assert client.get("/api/floor/tables").json() == []


def test_no_se_puede_colgar_una_mesa_de_la_zona_de_otra_sede(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """
    Sin esta comprobacion, mandar el uuid de una zona ajena crearia una mesa que
    aparece en el mapa de la otra sucursal.

    Y devuelve 404, no 403: un 403 confirmaria que esa zona existe.
    """
    principal, norte = sedes
    zona_del_norte = _zona(client, norte, "Interior")

    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    respuesta = client.post("/api/floor/tables", json={"number": 1, "sector_id": zona_del_norte})

    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["code"] == "no_encontrado"


def test_la_ruta_del_mapa_no_se_lee_como_un_uuid(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """
    `layout` es una ruta literal y va declarada ANTES de `/{mesa_id}`.

    En Starlette gana la primera que casa. Si estuvieran al reves, guardar el
    mapa intentaria leer «layout» como identificador y devolveria un error de
    validacion que no dice nada.
    """
    principal, _ = sedes
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))

    respuesta = client.patch("/api/floor/tables/layout", json={"tables": []})

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_mapa_se_guarda_entero(client: TestClient, sedes: tuple[Branch, Branch]) -> None:
    principal, _ = sedes
    zona = _zona(client, principal, "Interior")
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    uno = client.post("/api/floor/tables", json={"number": 1, "sector_id": zona}).json()
    dos = client.post("/api/floor/tables", json={"number": 2, "sector_id": zona}).json()

    guardadas = client.patch(
        "/api/floor/tables/layout",
        json={
            "tables": [
                {"id": uno["id"], "position_x": 10, "position_y": 20},
                {"id": dos["id"], "position_x": 30, "position_y": 40},
            ]
        },
    ).json()

    posiciones = {m["number"]: (m["position_x"], m["position_y"]) for m in guardadas}
    assert posiciones == {1: (10, 20), 2: (30, 40)}


def test_el_mapa_ignora_mesas_de_otra_sede(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """No es un error que haya que contar: esa mesa no existe para esta peticion."""
    principal, norte = sedes
    zona_norte = _zona(client, norte, "Interior")
    client.cookies.update(cookie_con(ESCRITOR, branch_id=norte.id))
    ajena = client.post("/api/floor/tables", json={"number": 9, "sector_id": zona_norte}).json()

    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    respuesta = client.patch(
        "/api/floor/tables/layout",
        json={"tables": [{"id": ajena["id"], "position_x": 1, "position_y": 1}]},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_estado_solo_marca_la_hora_cuando_cambia(
    client: TestClient, sedes: tuple[Branch, Branch]
) -> None:
    """
    `status_changed_at` es la marca para desempatar cuando dos dispositivos
    cambian la misma mesa. Tocarla en cada peticion la haria inutil.
    """
    principal, _ = sedes
    zona = _zona(client, principal, "Interior")
    client.cookies.update(cookie_con(ESCRITOR, branch_id=principal.id))
    mesa = client.post("/api/floor/tables", json={"number": 5, "sector_id": zona}).json()

    ocupada = client.patch(f"/api/floor/tables/{mesa['id']}/status", json={"status": "occupied"})
    assert ocupada.json()["status"] == "occupied"

    invalido = client.patch(f"/api/floor/tables/{mesa['id']}/status", json={"status": "volando"})
    assert invalido.status_code == 422
    assert invalido.json()["error"]["code"] == "estado_invalido"

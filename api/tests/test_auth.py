from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core import token_version
from app.core.security import COOKIE_ACCESO, COOKIE_REFRESCO, leer_acceso, leer_refresco
from app.models import Branch, RefreshToken, User
from tests.factories import crear_sucursal, crear_usuario


@pytest.fixture(autouse=True)
def _sin_cache() -> None:
    """La cache de revocacion es global; entre casos hay que vaciarla."""
    token_version.vaciar()


@pytest.fixture(name="sucursal")
def sucursal_fixture(session: Session) -> Branch:
    return crear_sucursal(session)


@pytest.fixture(name="ana")
def ana_fixture(session: Session, sucursal: Branch) -> User:
    return crear_usuario(session, sucursales=[sucursal])


# --- entrar con correo ------------------------------------------------------


def test_entrar_deja_las_dos_cookies_y_no_devuelve_hashes(client: TestClient, ana: User) -> None:
    respuesta = client.post(
        "/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"}
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["name"] == "Ana"
    # Los hashes no estan en el esquema publico, asi que no hay nada que excluir.
    assert "password_hash" not in cuerpo and "pin_hash" not in cuerpo

    assert COOKIE_ACCESO in respuesta.cookies
    assert COOKIE_REFRESCO in respuesta.cookies
    # httpOnly: el token no pasa por JavaScript.
    assert "httponly" in respuesta.headers["set-cookie"].lower()


def test_el_token_lleva_la_sucursal_activa(client: TestClient, ana: User, sucursal: Branch) -> None:
    """
    La sucursal viaja DENTRO del token firmado.

    Si viniera de una cabecera o de la query, operar en la sede de al lado seria
    cuestion de cambiar un campo del JSON.
    """
    respuesta = client.post(
        "/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"}
    )

    carga = leer_acceso(respuesta.cookies[COOKIE_ACCESO])
    assert carga["branch_id"] == str(sucursal.id)
    assert carga["branch_ids"] == [str(sucursal.id)]
    assert carga["login_method"] == "email"


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("ana@zentra.local", "la-que-no-es"),
        ("nadie@zentra.local", "Contrasena123"),
    ],
)
def test_una_credencial_mala_y_un_correo_inexistente_dan_EL_MISMO_error(
    client: TestClient, ana: User, email: str, password: str
) -> None:
    """
    Distinguirlos le regala al atacante un oraculo de que correos existen.

    Y el bloqueo por intentos, cuando llegue, tiene que responder tambien esto
    mismo: un 423 diria cuando volver a intentarlo.
    """
    respuesta = client.post("/api/auth/login", json={"email": email, "password": password})

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "credenciales_invalidas"
    assert respuesta.json()["error"]["message"] == "Correo o contrasena incorrectos."


def test_un_usuario_desactivado_no_entra(
    client: TestClient, session: Session, sucursal: Branch
) -> None:
    crear_usuario(session, email="fuera@zentra.local", is_active=False, sucursales=[sucursal])

    respuesta = client.post(
        "/api/auth/login", json={"email": "fuera@zentra.local", "password": "Contrasena123"}
    )

    assert respuesta.status_code == 401


def test_dos_inicios_en_el_mismo_segundo_no_chocan(client: TestClient, ana: User) -> None:
    """
    El bug que LoklFlow descubrio en produccion.

    La carga del refresco es determinista y el `iat` va en segundos, asi que sin
    un `jti` unico dos inicios del mismo usuario en el mismo segundo producen un
    JWT byte a byte identico y el segundo choca contra la clave de la tabla: un
    500 en un caso que pasa de verdad, el operario que toca dos veces porque la
    primera no respondio.
    """
    credenciales = {"email": "ana@zentra.local", "password": "Contrasena123"}

    primero = client.post("/api/auth/login", json=credenciales)
    segundo = client.post("/api/auth/login", json=credenciales)

    assert primero.status_code == 200
    assert segundo.status_code == 200
    assert primero.cookies[COOKIE_REFRESCO] != segundo.cookies[COOKIE_REFRESCO]


# --- entrar con PIN ---------------------------------------------------------


def test_entrar_con_pin_da_una_sesion_mas_larga(
    client: TestClient, session: Session, sucursal: Branch
) -> None:
    """
    Un mesero no puede reautenticarse a mitad de servicio.

    Por eso el acceso por PIN dura horas y no minutos. El refresco, al reves:
    menos que el del correo, porque cuatro digitos son una credencial debil y la
    tableta se queda en la barra toda la noche.
    """
    mesero = crear_usuario(
        session, name="Luis", email=None, password=None, pin="8264", sucursales=[sucursal]
    )

    respuesta = client.post("/api/auth/pin", json={"user_id": str(mesero.id), "pin": "8264"})

    assert respuesta.status_code == 200
    acceso = leer_acceso(respuesta.cookies[COOKIE_ACCESO])
    refresco = leer_refresco(respuesta.cookies[COOKIE_REFRESCO])
    assert acceso["login_method"] == "pin"
    assert acceso["exp"] - acceso["iat"] == 4 * 3600
    assert refresco["exp"] - refresco["iat"] == 12 * 3600


def test_un_pin_malo_no_dice_si_el_usuario_existe(
    client: TestClient, session: Session, sucursal: Branch
) -> None:
    mesero = crear_usuario(
        session, name="Luis", email=None, password=None, pin="8264", sucursales=[sucursal]
    )

    malo = client.post("/api/auth/pin", json={"user_id": str(mesero.id), "pin": "1357"})
    inexistente = client.post("/api/auth/pin", json={"user_id": str(uuid4()), "pin": "1357"})

    assert malo.status_code == inexistente.status_code == 401
    assert malo.json()["error"] == inexistente.json()["error"]


# --- renovar ----------------------------------------------------------------


def test_renovar_rota_el_refresco_y_conserva_el_metodo(
    client: TestClient, session: Session, sucursal: Branch
) -> None:
    """
    El metodo se propaga del token viejo.

    Fijarlo a «correo» degradaria una sesion de PIN de cuatro horas a quince
    minutos, y el mesero acabaria en el formulario de correo, donde no tiene
    credenciales que poner.
    """
    mesero = crear_usuario(
        session, name="Luis", email=None, password=None, pin="8264", sucursales=[sucursal]
    )
    client.post("/api/auth/pin", json={"user_id": str(mesero.id), "pin": "8264"})
    viejo = client.cookies[COOKIE_REFRESCO]

    respuesta = client.post("/api/auth/refresh")

    assert respuesta.status_code == 200
    nuevo = respuesta.cookies[COOKIE_REFRESCO]
    assert nuevo != viejo
    assert leer_acceso(respuesta.cookies[COOKIE_ACCESO])["login_method"] == "pin"


def test_un_refresco_ya_usado_no_vale(client: TestClient, ana: User) -> None:
    client.post("/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"})
    viejo = client.cookies[COOKIE_REFRESCO]
    client.post("/api/auth/refresh")

    client.cookies.set(COOKIE_REFRESCO, viejo)
    respuesta = client.post("/api/auth/refresh")

    assert respuesta.status_code == 401


def test_reusar_un_refresco_revoca_la_cadena_entera(
    client: TestClient, session: Session, ana: User
) -> None:
    """
    Si un token viejo esta circulando, el actual tambien puede estarlo.

    Rechazar solo el reutilizado dejaria viva la sesion del ladron. Se revocan
    todos los refrescos del usuario y se sube su `token_version`, que invalida
    tambien los tokens de acceso que ya estan por ahi.
    """
    client.post("/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"})
    robado = client.cookies[COOKIE_REFRESCO]
    client.post("/api/auth/refresh")  # rota: el robado queda revocado y con sucesor
    version_antes = session.get(User, ana.id).token_version

    client.cookies.set(COOKIE_REFRESCO, robado)
    assert client.post("/api/auth/refresh").status_code == 401

    session.expire_all()
    assert session.get(User, ana.id).token_version == version_antes + 1
    vivos = session.exec(
        select(RefreshToken)
        .where(RefreshToken.user_id == ana.id)
        .where(col(RefreshToken.revoked_at).is_(None))
    ).all()
    assert vivos == []


# --- cerrar sesion y /me ----------------------------------------------------


def test_cerrar_sesion_revoca_el_refresco(client: TestClient, ana: User) -> None:
    client.post("/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"})
    refresco = client.cookies[COOKIE_REFRESCO]

    assert client.post("/api/auth/logout").status_code == 204

    client.cookies.set(COOKIE_REFRESCO, refresco)
    assert client.post("/api/auth/refresh").status_code == 401


def test_me_necesita_sesion(client: TestClient) -> None:
    respuesta = client.get("/api/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "sin_sesion"


def test_me_dice_quien_eres_y_donde(client: TestClient, ana: User, sucursal: Branch) -> None:
    client.post("/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"})

    cuerpo = client.get("/api/auth/me").json()

    assert cuerpo["name"] == "Ana"
    assert cuerpo["branch_id"] == str(sucursal.id)


def test_un_token_de_otro_secreto_no_cuela(client: TestClient, ana: User) -> None:
    falso = jwt.encode({"sub": str(ana.id), "name": "Ana", "branch_id": str(uuid4())}, "otro")
    client.cookies.set(COOKIE_ACCESO, falso)

    respuesta = client.get("/api/auth/me")

    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "token_invalido"


def test_subir_el_contador_cierra_las_sesiones_abiertas(
    client: TestClient, session: Session, ana: User
) -> None:
    """
    La revocacion sin consultar la base en cada peticion.

    Los permisos viajan en el token para que el guard no haga una consulta por
    peticion; `token_version` es lo que permite invalidar un token ya emitido
    sin renunciar a eso.
    """
    client.post("/api/auth/login", json={"email": "ana@zentra.local", "password": "Contrasena123"})
    assert client.get("/api/auth/me").status_code == 200

    usuario = session.get(User, ana.id)
    usuario.token_version += 1
    session.add(usuario)
    session.commit()
    token_version.invalidar(ana.id)

    respuesta = client.get("/api/auth/me")
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["code"] == "sesion_revocada"

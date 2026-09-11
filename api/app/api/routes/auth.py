from fastapi import APIRouter, Request, Response, status

from app.core.deps import SesionActual, SessionDep
from app.core.security import COOKIE_ACCESO, COOKIE_REFRESCO, opciones_de_cookie
from app.models import LoginPorCorreo, LoginPorPin, UserPublic
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["sesion"])


def _poner_cookies(respuesta: Response, emitida: auth_service.SesionEmitida) -> None:
    opciones = opciones_de_cookie()
    respuesta.set_cookie(COOKIE_ACCESO, emitida.acceso, **opciones)
    respuesta.set_cookie(COOKIE_REFRESCO, emitida.refresco, **opciones)


@router.post("/login", summary="Entrar con correo y contrasena")
def login(datos: LoginPorCorreo, session: SessionDep, respuesta: Response) -> UserPublic:
    emitida = auth_service.entrar_por_correo(session, datos.email, datos.password)
    _poner_cookies(respuesta, emitida)
    return UserPublic.model_validate(emitida.usuario, from_attributes=True)


@router.post("/pin", summary="Entrar con PIN")
def login_pin(datos: LoginPorPin, session: SessionDep, respuesta: Response) -> UserPublic:
    emitida = auth_service.entrar_por_pin(session, datos.user_id, datos.pin)
    _poner_cookies(respuesta, emitida)
    return UserPublic.model_validate(emitida.usuario, from_attributes=True)


@router.post("/refresh", summary="Renovar la sesion")
def refresh(peticion: Request, session: SessionDep, respuesta: Response) -> UserPublic:
    emitida = auth_service.renovar(session, peticion.cookies.get(COOKIE_REFRESCO, ""))
    _poner_cookies(respuesta, emitida)
    return UserPublic.model_validate(emitida.usuario, from_attributes=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesion")
def logout(peticion: Request, session: SessionDep, respuesta: Response) -> None:
    auth_service.salir(session, peticion.cookies.get(COOKIE_REFRESCO))
    # Los MISMOS atributos que al ponerlas. Con un `secure` o un `samesite`
    # distinto, varios navegadores no reconocen la cookie como la misma y la
    # sesion SOBREVIVE al cierre.
    opciones = opciones_de_cookie()
    respuesta.delete_cookie(COOKIE_ACCESO, path=opciones["path"], samesite=opciones["samesite"])
    respuesta.delete_cookie(COOKIE_REFRESCO, path=opciones["path"], samesite=opciones["samesite"])


@router.get("/me", summary="Quien soy")
def me(sesion: SesionActual) -> dict:
    return {
        "id": str(sesion.sub),
        "name": sesion.name,
        "email": sesion.email,
        "branch_id": str(sesion.branch_id),
        "branch_ids": [str(b) for b in sesion.branch_ids],
        "login_method": sesion.login_method,
        "permissions": sesion.permissions,
    }

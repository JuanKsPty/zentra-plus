from fastapi import APIRouter, Depends
from sqlmodel import select

from app.core import permissions as P
from app.core.deps import SessionDep, requiere
from app.core.errors import ErrorAplicacion
from app.models import BusinessConfig, BusinessConfigPublic, BusinessConfigUpdate

router = APIRouter(prefix="/business-config", tags=["configuracion"])


def _fila(session: SessionDep) -> BusinessConfig:
    configuracion = session.exec(select(BusinessConfig)).first()
    if configuracion is None:
        # La siembra la crea. Si falta, el problema es que nadie sembro, y
        # decirlo asi ahorra media hora de buscar un endpoint roto.
        raise ErrorAplicacion(
            409,
            "sin_configuracion",
            "El negocio no esta configurado todavia. Ejecuta la siembra.",
        )
    return configuracion


@router.get("", dependencies=[Depends(requiere(P.SETTINGS_READ))], summary="Datos del negocio")
def leer(session: SessionDep) -> BusinessConfigPublic:
    return BusinessConfigPublic.model_validate(_fila(session), from_attributes=True)


@router.put("", dependencies=[Depends(requiere(P.SETTINGS_WRITE))], summary="Cambiar los datos")
def actualizar(datos: BusinessConfigUpdate, session: SessionDep) -> BusinessConfigPublic:
    configuracion = _fila(session)

    # `exclude_unset`: solo se toca lo que vino. Sin esto, un formulario que
    # manda tres campos borraria los otros cuatro poniendolos a null.
    for campo, valor in datos.model_dump(exclude_unset=True).items():
        setattr(configuracion, campo, valor)

    session.add(configuracion)
    session.commit()
    session.refresh(configuracion)
    return BusinessConfigPublic.model_validate(configuracion, from_attributes=True)

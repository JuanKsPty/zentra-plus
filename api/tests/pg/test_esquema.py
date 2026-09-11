from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.conflicts import es_conflicto_concurrente, restriccion_violada
from app.models import Branch, BranchCounter, BusinessConfig, User


def test_el_esquema_se_construye_desde_cero(base_vacia: Session) -> None:
    """
    `alembic upgrade head` sobre una base vacia, en cada ejecucion.

    Sin esto, una base que se fue parcheando durante meses funciona sin que
    nadie sepa que ya no se puede recrear — y eso no se descubre hasta que hace
    falta levantar un entorno nuevo, normalmente con prisa.
    """
    tablas = {
        fila[0]
        for fila in base_vacia.exec(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
    }

    assert {
        "alembic_version",
        "branches",
        "branch_counters",
        "business_config",
        "permissions",
        "refresh_tokens",
        "role_permissions",
        "roles",
        "user_branches",
        "users",
    } <= tablas


def test_solo_puede_haber_una_configuracion(base_vacia: Session) -> None:
    """El indice sobre `((true))`: la segunda fila choca contra la base."""
    base_vacia.add(BusinessConfig(business_name="Primera"))
    base_vacia.commit()

    base_vacia.add(BusinessConfig(business_name="Segunda"))
    with pytest.raises(IntegrityError) as excinfo:
        base_vacia.commit()
    base_vacia.rollback()

    assert es_conflicto_concurrente(excinfo.value)
    assert restriccion_violada(excinfo.value) == "uq_business_config_fila_unica"


def test_un_usuario_sin_ninguna_credencial_no_se_guarda(base_vacia: Session) -> None:
    """
    El CHECK que el autogenerate no escribe.

    Una fila sin contrasena ni PIN no puede entrar por ningun sitio: solo sirve
    para confundir a quien mire la tabla de empleados.
    """
    base_vacia.add(User(name="Fantasma", email="fantasma@zentra.local"))

    with pytest.raises(IntegrityError) as excinfo:
        base_vacia.commit()
    base_vacia.rollback()

    assert restriccion_violada(excinfo.value) == "ck_users_alguna_credencial"


def test_el_codigo_de_sucursal_es_unico(base_vacia: Session) -> None:
    base_vacia.add(Branch(name="Principal", code="PRIN"))
    base_vacia.commit()

    base_vacia.add(Branch(name="Otra con el mismo codigo", code="PRIN"))
    with pytest.raises(IntegrityError):
        base_vacia.commit()
    base_vacia.rollback()


def test_borrar_una_sucursal_se_lleva_su_contador(base_vacia: Session) -> None:
    sucursal = Branch(name="Norte", code="NOR")
    base_vacia.add(sucursal)
    base_vacia.commit()
    base_vacia.refresh(sucursal)
    base_vacia.add(BranchCounter(branch_id=sucursal.id))
    base_vacia.commit()

    base_vacia.delete(sucursal)
    base_vacia.commit()

    assert base_vacia.exec(select(BranchCounter)).all() == []


def test_los_importes_van_y_vuelven_exactos(base_vacia: Session) -> None:
    """
    La razon de que el dinero sea `numeric` y no float, comprobada.

    SQLite no tiene NUMERIC real y devuelve float, asi que un total de 19.99
    vuelve como 19.989999999999998 y NINGUNA prueba en memoria lo ve. Aqui si.
    """
    base_vacia.add(BusinessConfig(business_name="Cafe", tax_rate=Decimal("0.07")))
    base_vacia.commit()
    base_vacia.expire_all()

    leida = base_vacia.exec(select(BusinessConfig)).one()

    assert leida.tax_rate == Decimal("0.07")
    assert isinstance(leida.tax_rate, Decimal)


def test_las_fechas_conservan_la_zona(base_vacia: Session) -> None:
    """
    `timestamptz` y no `timestamp`.

    Un timestamp sin zona escrito por un proceso en UTC y leido por uno en hora
    local es como se pierde la ultima madrugada de un reporte, y en un runner de
    CI —que va en UTC— el fallo es invisible.
    """
    sucursal = Branch(name="Sur", code="SUR")
    base_vacia.add(sucursal)
    base_vacia.commit()
    base_vacia.expire_all()

    leida = base_vacia.exec(select(Branch).where(Branch.code == "SUR")).one()

    assert leida.created_at.tzinfo is not None
    assert leida.created_at <= datetime.now(UTC)
    assert uuid4() != leida.id


def test_el_numero_de_mesa_es_unico_POR_SUCURSAL(base_vacia: Session) -> None:
    """
    La unicidad que cambio al pasar a multisucursal.

    En LoklFlow el numero era unico global, asi que la segunda sede no podia
    tener una «mesa 1». Aqui las dos pueden, y dos mesas 1 en la MISMA sede no.
    """
    from app.models import RestaurantTable, Sector

    sedes = [Branch(name="Principal", code="PRIN"), Branch(name="Norte", code="NOR")]
    base_vacia.add_all(sedes)
    base_vacia.commit()
    for sede in sedes:
        base_vacia.refresh(sede)

    zonas = [Sector(branch_id=sede.id, name="Interior") for sede in sedes]
    base_vacia.add_all(zonas)
    base_vacia.commit()
    for zona in zonas:
        base_vacia.refresh(zona)

    # Una mesa 1 en cada sede: permitido.
    for sede, zona in zip(sedes, zonas, strict=True):
        base_vacia.add(RestaurantTable(branch_id=sede.id, sector_id=zona.id, number=1))
    base_vacia.commit()

    # Una segunda mesa 1 en la misma sede: no.
    base_vacia.add(RestaurantTable(branch_id=sedes[0].id, sector_id=zonas[0].id, number=1))
    with pytest.raises(IntegrityError) as excinfo:
        base_vacia.commit()
    base_vacia.rollback()

    # Y llega con el NOMBRE del indice, que es lo que permite dar el mensaje
    # concreto. SQLite no expone esto, asi que solo se puede comprobar aqui.
    assert restriccion_violada(excinfo.value) == "uq_tables_numero_por_sucursal"


def test_una_estacion_inventada_no_entra_ni_por_sql(base_vacia: Session) -> None:
    """El CHECK que se escribio a mano: el autogenerate no los genera."""
    from app.models import Product

    base_vacia.add(Product(name="Cafe", price=Decimal("1.50"), station="terraza"))

    with pytest.raises(IntegrityError) as excinfo:
        base_vacia.commit()
    base_vacia.rollback()

    assert restriccion_violada(excinfo.value) == "ck_products_estacion"

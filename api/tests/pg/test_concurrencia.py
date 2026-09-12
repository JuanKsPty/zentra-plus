"""
Lo que solo se puede comprobar con concurrencia de verdad.

SQLite serializa las escrituras, asi que una prueba de carreras ahi pasa siempre
y no demuestra nada. Estas corren contra PostgreSQL.
"""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from uuid import UUID

import pytest
from sqlmodel import Session, create_engine, select

from app.models import Branch, BranchCounter
from app.services.numbering import siguiente_numero

from .conftest import URL


def _pedir_numero(branch_id: UUID) -> int:
    # Cada hilo con su propia conexion: compartir una sesion entre hilos no
    # probaria concurrencia, probaria un error de uso.
    motor = create_engine(URL)
    with Session(motor) as sesion:
        numero = siguiente_numero(sesion, branch_id)
        sesion.commit()
    motor.dispose()
    return numero


def test_veinte_hilos_obtienen_veinte_numeros_consecutivos(base_vacia: Session) -> None:
    """
    LA prueba que justifica el diseno del contador.

    Con `MAX(order_number) + 1`, veinte lecturas simultaneas ven el mismo maximo
    y entregan el mismo numero; con reintentos, los reintentos vuelven a chocar
    entre si. Es el bug que LoklFlow arrastro hasta produccion.

    Con `UPDATE ... RETURNING`, PostgreSQL bloquea la fila y la segunda peticion
    ESPERA al commit de la primera: no falla, espera. El resultado tiene que ser
    exactamente 1..20, sin repetidos y sin huecos.
    """
    sucursal = Branch(name="Principal", code="PRIN")
    base_vacia.add(sucursal)
    base_vacia.commit()
    base_vacia.refresh(sucursal)
    base_vacia.add(BranchCounter(branch_id=sucursal.id))
    base_vacia.commit()

    # El identificador se saca ANTES del pool. Leerlo dentro de los hilos
    # dispara una carga perezosa sobre la sesion compartida desde veinte sitios
    # a la vez, y SQLAlchemy lo rechaza — un fallo de la prueba que se disfraza
    # de fallo de concurrencia del codigo.
    sucursal_id = sucursal.id

    with ThreadPoolExecutor(max_workers=20) as pool:
        numeros = sorted(pool.map(lambda _: _pedir_numero(sucursal_id), range(20)))

    assert numeros == list(range(1, 21))
    assert len(set(numeros)) == 20


def test_cada_sucursal_lleva_su_propia_cuenta(base_vacia: Session) -> None:
    sedes = [Branch(name="Principal", code="PRIN"), Branch(name="Norte", code="NOR")]
    base_vacia.add_all(sedes)
    base_vacia.commit()
    for sede in sedes:
        base_vacia.refresh(sede)
        base_vacia.add(BranchCounter(branch_id=sede.id))
    base_vacia.commit()

    identificadores = [sede.id for sede in sedes]

    with ThreadPoolExecutor(max_workers=10) as pool:
        tareas = [
            pool.submit(_pedir_numero, sucursal_id)
            for sucursal_id in identificadores
            for _ in range(5)
        ]
        for tarea in tareas:
            tarea.result()

    base_vacia.expire_all()
    contadores = base_vacia.exec(select(BranchCounter)).all()

    assert sorted(c.last_order_number for c in contadores) == [5, 5]


def test_una_sucursal_sin_contador_lo_siembra_al_vuelo(base_vacia: Session) -> None:
    """
    Una sucursal sin contador no puede recibir comandas, y descubrirlo a media
    hora punta es lo que hay que evitar.
    """
    sucursal = Branch(name="Sur", code="SUR")
    base_vacia.add(sucursal)
    base_vacia.commit()
    base_vacia.refresh(sucursal)

    assert _pedir_numero(sucursal.id) == 1
    assert _pedir_numero(sucursal.id) == 2


def _abrir_caja(branch_id: UUID, cajero_id: UUID) -> str:
    """Devuelve 'abierto' o el nombre de la restriccion que lo impidio."""
    from sqlalchemy.exc import IntegrityError

    from app.core.conflicts import restriccion_violada
    from app.models import Shift

    motor = create_engine(URL)
    try:
        with Session(motor) as sesion:
            sesion.add(
                Shift(
                    branch_id=branch_id,
                    opened_by=cajero_id,
                    opening_cash=Decimal("50.00"),
                    status="open",
                )
            )
            try:
                sesion.commit()
                return "abierto"
            except IntegrityError as error:
                sesion.rollback()
                return restriccion_violada(error) or "otro"
    finally:
        motor.dispose()


def test_un_doble_clic_no_abre_dos_cajas(base_vacia: Session) -> None:
    """
    El indice parcial unico, bajo concurrencia de verdad.

    La comprobacion previa del servicio es un leer-antes-de-escribir: entre la
    lectura y la escritura hay una ventana, y un doble clic cabe de sobra. Sin
    el indice, los dos turnos se abren, los cobros se reparten entre ellos y NO
    CUADRA NINGUNO — peor que no cuadrar uno, porque nadie sabe cual mirar.

    SQLite serializa las escrituras, asi que ahi esta prueba pasaria siempre sin
    demostrar nada.
    """
    from app.core.security import hashear
    from app.models import Branch, User

    sucursal = Branch(name="Principal", code="PRIN")
    cajero = User(name="Caja", email="caja@zentra.local", password_hash=hashear("x"))
    base_vacia.add_all([sucursal, cajero])
    base_vacia.commit()
    base_vacia.refresh(sucursal)
    base_vacia.refresh(cajero)
    sucursal_id, cajero_id = sucursal.id, cajero.id

    with ThreadPoolExecutor(max_workers=8) as pool:
        resultados = list(pool.map(lambda _: _abrir_caja(sucursal_id, cajero_id), range(8)))

    assert resultados.count("abierto") == 1
    # Y los demas caen por el indice CON SU NOMBRE, que es lo que permite
    # traducirlo a «ya tienes una caja abierta» y no a un 500.
    assert set(resultados) - {"abierto"} == {"idx_shifts_un_abierto_por_cajero_y_sucursal"}


def test_el_mismo_cajero_puede_tener_caja_en_dos_sucursales(base_vacia: Session) -> None:
    """
    El indice es por cajero Y SUCURSAL. Con uno solo sobre el cajero, un gerente
    no podria cubrir dos sedes.
    """
    from app.core.security import hashear
    from app.models import Branch, User

    sedes = [Branch(name="Principal", code="PRIN"), Branch(name="Norte", code="NOR")]
    cajero = User(name="Caja", email="caja@zentra.local", password_hash=hashear("x"))
    base_vacia.add_all([*sedes, cajero])
    base_vacia.commit()
    for sede in sedes:
        base_vacia.refresh(sede)
    base_vacia.refresh(cajero)

    resultados = [_abrir_caja(sede.id, cajero.id) for sede in sedes]

    assert resultados == ["abierto", "abierto"]


def test_una_clave_de_reenvio_se_usa_una_sola_vez(base_vacia: Session) -> None:
    """
    El otro indice parcial. Solo indexa las filas que traen clave, que son las
    menos — en PostgreSQL varios NULL no chocan de todas formas.
    """
    from sqlalchemy.exc import IntegrityError

    from app.core.conflicts import restriccion_violada
    from app.models import Branch, BranchCounter, Order, Payment

    sucursal = Branch(name="Principal", code="PRIN")
    base_vacia.add(sucursal)
    base_vacia.commit()
    base_vacia.refresh(sucursal)
    base_vacia.add(BranchCounter(branch_id=sucursal.id))

    # El cobro cuelga de una comanda de verdad: `order_id` es clave foranea, y
    # un uuid inventado cae por la foranea antes de llegar al indice que se
    # quiere probar.
    cuenta = Order(branch_id=sucursal.id, order_number=1, total=Decimal("50.00"))
    base_vacia.add(cuenta)
    base_vacia.commit()
    base_vacia.refresh(cuenta)

    def cobro(clave: str | None) -> Payment:
        return Payment(
            branch_id=sucursal.id,
            order_id=cuenta.id,
            method="cash",
            amount=Decimal("5.00"),
            client_request_id=clave,
        )

    # Sin clave: caben todos los que quieran.
    base_vacia.add_all([cobro(None), cobro(None)])
    base_vacia.commit()

    base_vacia.add(cobro("abc"))
    base_vacia.commit()
    base_vacia.add(cobro("abc"))

    with pytest.raises(IntegrityError) as excinfo:
        base_vacia.commit()
    base_vacia.rollback()

    assert restriccion_violada(excinfo.value) == "idx_payments_client_request_id"

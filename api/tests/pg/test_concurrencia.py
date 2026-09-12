"""
Lo que solo se puede comprobar con concurrencia de verdad.

SQLite serializa las escrituras, asi que una prueba de carreras ahi pasa siempre
y no demuestra nada. Estas corren contra PostgreSQL.
"""

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID

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

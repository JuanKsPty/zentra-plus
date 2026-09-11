"""
La red que hace que olvidarse del alcance sea imposible, no improbable.

`app/db/scoping.py` da un unico constructor de consultas que EXIGE el alcance.
Nada impide escribir `select(Order)` a pelo y saltarselo — salvo esto, que lee
el arbol sintactico de los servicios y las rutas y lo denuncia.

Se lee el codigo en vez de ejercitarlo porque el fallo NO TIENE SINTOMA: una
consulta sin filtro devuelve mas filas, no menos, y en una instalacion con una
sola sucursal se comporta exactamente igual que la correcta. El dia que se abre
la segunda sede, la comanda de un local aparece en el tablero del otro.

Si de verdad hace falta una consulta sin filtrar, se marca en la misma linea:

    session.exec(select(Order))  # scoping: informe del dueno, ya filtrado arriba
"""

import ast
from pathlib import Path

from app.models.base import ConSucursal

RAIZ = Path(__file__).resolve().parent.parent / "app"
CARPETAS_VIGILADAS = ("services", "api")
MARCA_DE_EXCEPCION = "# scoping:"


def buscar_consultas_a_pelo(codigo: str, modelos: set[str], origen: str = "<codigo>") -> list[str]:
    """
    Las llamadas a `select(Modelo)` sobre un modelo con sucursal, sin la marca.

    Esta separado del recorrido de archivos para poder probar el escaner con un
    fragmento sintetico: un guardian cuya unica prueba es «no encontre nada»
    sigue en verde el dia que deja de mirar.
    """
    lineas = codigo.splitlines()
    culpables: list[str] = []

    for nodo in ast.walk(ast.parse(codigo, filename=origen)):
        if not isinstance(nodo, ast.Call):
            continue
        if not (isinstance(nodo.func, ast.Name) and nodo.func.id == "select"):
            continue
        if not nodo.args:
            continue

        primero = nodo.args[0]
        if not (isinstance(primero, ast.Name) and primero.id in modelos):
            continue

        linea = lineas[nodo.lineno - 1] if nodo.lineno <= len(lineas) else ""
        if MARCA_DE_EXCEPCION in linea:
            continue

        culpables.append(f"{origen}:{nodo.lineno}  select({primero.id})")

    return culpables


def modelos_con_sucursal() -> set[str]:
    """Los nombres de clase de toda tabla que lleva sucursal."""
    import app.models  # noqa: F401  (registra las subclases)

    pendientes = [ConSucursal]
    nombres: set[str] = set()
    while pendientes:
        clase = pendientes.pop()
        for hija in clase.__subclasses__():
            nombres.add(hija.__name__)
            pendientes.append(hija)
    return nombres


def test_sin_consultas_a_pelo_sobre_tablas_con_sucursal() -> None:
    modelos = modelos_con_sucursal()
    culpables: list[str] = []

    for carpeta in CARPETAS_VIGILADAS:
        for archivo in sorted((RAIZ / carpeta).rglob("*.py")):
            culpables += buscar_consultas_a_pelo(
                archivo.read_text(encoding="utf-8"),
                modelos,
                origen=str(archivo.relative_to(RAIZ.parent)),
            )

    assert not culpables, (
        "Estas consultas se saltan el alcance por sucursal:\n  "
        + "\n  ".join(culpables)
        + "\n\nUsa `consulta(Modelo, alcance)` de app/db/scoping.py. Si de verdad hace "
        f"falta sin filtrar, marcala con `{MARCA_DE_EXCEPCION} <motivo>` en la misma linea."
    )


# --- que el guardian sepa mirar ---------------------------------------------

_FRAGMENTO = """
from sqlmodel import select

from app.models import Comanda, Producto


def listar(session, alcance):
    a = session.exec(select(Comanda)).all()
    b = session.exec(consulta(Comanda, alcance)).all()
    c = session.exec(select(Producto)).all()
    return a, b, c
"""


def test_el_guardian_detecta_una_consulta_sin_filtro() -> None:
    culpables = buscar_consultas_a_pelo(_FRAGMENTO, {"Comanda"})

    assert len(culpables) == 1
    assert "select(Comanda)" in culpables[0]


def test_el_guardian_no_se_queja_del_catalogo() -> None:
    """`Producto` no lleva sucursal: consultarlo entero es lo correcto."""
    assert not buscar_consultas_a_pelo(_FRAGMENTO.replace("Comanda", "Producto"), {"Comanda"})


def test_la_marca_de_excepcion_silencia_esa_linea_y_solo_esa() -> None:
    con_marca = _FRAGMENTO.replace(
        "a = session.exec(select(Comanda)).all()",
        "a = session.exec(select(Comanda)).all()  # scoping: motivo explicado",
    )

    assert not buscar_consultas_a_pelo(con_marca, {"Comanda"})
    # Y la marca no vale para el archivo entero: otra linea sin marca sigue cayendo.
    assert buscar_consultas_a_pelo(con_marca + "\nx = select(Comanda)\n", {"Comanda"})

"""
El catalogo de permisos. Constantes, nunca cadenas sueltas.

Un permiso mal escrito en una cadena suelta no falla: deniega para siempre, en
silencio, y se descubre cuando alguien no puede trabajar. Aqui la dependencia
valida el nombre AL IMPORTAR, asi que `requiere("orders:crate")` revienta el
arranque en vez de convertirse en una puerta cerrada permanente.

Se usa `read`/`write` en vez del CRUD de cuatro verbos: en la practica nadie
separa crear de editar, y dos permisos por modulo son dos casillas en la pantalla
de roles en vez de cuatro.

Nombres respecto a LoklFlow: `menu` pasa a `catalog`, `tables` a `floor` y `pos`
a `cash`. El tercero importa — `pos:create` cubria cobrar, aplicar propina y
abrir turno, que son tres cosas que un negocio va a querer separar.
"""

from typing import Final

# --- personas y accesos -----------------------------------------------------
USERS_READ: Final = "users:read"
USERS_WRITE: Final = "users:write"
ROLES_READ: Final = "roles:read"
ROLES_WRITE: Final = "roles:write"

# --- sucursales -------------------------------------------------------------
BRANCHES_READ: Final = "branches:read"
BRANCHES_WRITE: Final = "branches:write"
# El consolidado. Sin esto, `?branch=all` da 403 aunque el usuario alcance
# varias sedes: ver el negocio entero es una decision aparte de operar en el.
BRANCHES_READ_ALL: Final = "branches:read_all"

# --- catalogo y salon -------------------------------------------------------
CATALOG_READ: Final = "catalog:read"
CATALOG_WRITE: Final = "catalog:write"
FLOOR_READ: Final = "floor:read"
FLOOR_WRITE: Final = "floor:write"

# --- servicio ---------------------------------------------------------------
ORDERS_READ: Final = "orders:read"
ORDERS_WRITE: Final = "orders:write"
# Avanzar el estado desde cocina no es lo mismo que editar una comanda: la
# cocina marca «lista» pero no anade lineas ni cambia cantidades.
ORDERS_BUMP: Final = "orders:bump"

# --- dinero -----------------------------------------------------------------
CASH_READ: Final = "cash:read"
CASH_WRITE: Final = "cash:write"

# --- existencias y reportes -------------------------------------------------
STOCK_READ: Final = "stock:read"
STOCK_WRITE: Final = "stock:write"
REPORTS_READ: Final = "reports:read"

# --- configuracion ----------------------------------------------------------
SETTINGS_READ: Final = "settings:read"
SETTINGS_WRITE: Final = "settings:write"


TODOS: Final[tuple[str, ...]] = (
    USERS_READ,
    USERS_WRITE,
    ROLES_READ,
    ROLES_WRITE,
    BRANCHES_READ,
    BRANCHES_WRITE,
    BRANCHES_READ_ALL,
    CATALOG_READ,
    CATALOG_WRITE,
    FLOOR_READ,
    FLOOR_WRITE,
    ORDERS_READ,
    ORDERS_WRITE,
    ORDERS_BUMP,
    CASH_READ,
    CASH_WRITE,
    STOCK_READ,
    STOCK_WRITE,
    REPORTS_READ,
    SETTINGS_READ,
    SETTINGS_WRITE,
)

CONOCIDOS: Final[frozenset[str]] = frozenset(TODOS)


def partir(permiso: str) -> tuple[str, str]:
    modulo, _, accion = permiso.partition(":")
    return modulo, accion


# --- roles de sistema -------------------------------------------------------
#
# Se siembran y se protegen del borrado. Sus permisos se REESCRIBEN en cada
# siembra: asi, anadir un permiso a «Cajero» aqui llega a la base sin migracion.

ADMINISTRADOR: Final = "Administrador"
GERENTE: Final = "Gerente"
CAJERO: Final = "Cajero"
MESERO: Final = "Mesero"
COCINA: Final = "Cocina"

ROLES_DE_SISTEMA: Final[dict[str, tuple[str, tuple[str, ...]]]] = {
    ADMINISTRADOR: ("Acceso total, incluida la configuracion y los roles", TODOS),
    GERENTE: (
        "Opera el negocio y ve los numeros; no toca roles ni configuracion",
        (
            USERS_READ,
            USERS_WRITE,
            ROLES_READ,
            BRANCHES_READ,
            BRANCHES_READ_ALL,
            CATALOG_READ,
            CATALOG_WRITE,
            FLOOR_READ,
            FLOOR_WRITE,
            ORDERS_READ,
            ORDERS_WRITE,
            ORDERS_BUMP,
            CASH_READ,
            CASH_WRITE,
            STOCK_READ,
            STOCK_WRITE,
            REPORTS_READ,
            SETTINGS_READ,
        ),
    ),
    CAJERO: (
        "Cobra y cierra turno",
        (
            BRANCHES_READ,
            CATALOG_READ,
            FLOOR_READ,
            ORDERS_READ,
            ORDERS_WRITE,
            CASH_READ,
            CASH_WRITE,
            # Necesario para imprimir el recibo: ahi van el nombre fiscal y el
            # pie del negocio.
            SETTINGS_READ,
        ),
    ),
    MESERO: (
        "Toma comandas y mueve el salon",
        (
            BRANCHES_READ,
            CATALOG_READ,
            FLOOR_READ,
            FLOOR_WRITE,
            ORDERS_READ,
            ORDERS_WRITE,
        ),
    ),
    COCINA: (
        "Ve el tablero y avanza el estado de lo que prepara",
        (
            BRANCHES_READ,
            CATALOG_READ,
            ORDERS_READ,
            ORDERS_BUMP,
        ),
    ),
}

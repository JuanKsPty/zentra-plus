"""
El sobre de un evento de tiempo real.

Se fija AQUI y en el primer commit del canal. Si el primer evento se mandara
plano y luego hubiera que meterle la sucursal, habria que tocar cada emisor y
cada suscriptor a la vez — y mientras tanto las dos versiones conviven en
pantallas distintas.

El evento es una SENAL, no un canal de datos: dice «mira otra vez», y quien lo
recibe vuelve a pedir. Asi un evento perdido por una reconexion no pierde nada,
porque el estado sigue estando en la base.
"""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

# Los canales. Un cliente se suscribe a los que sus permisos le permitan.
Canal = Literal["orders", "floor", "cash"]

TipoDeEvento = Literal[
    "order.created",
    "order.changed",
    "table.changed",
    "shift.changed",
]


def sobre(
    tipo: TipoDeEvento,
    branch_id: UUID,
    **payload: Any,
) -> dict[str, Any]:
    return {
        "tipo": tipo,
        "branchId": str(branch_id),
        "emitidoEn": datetime.now(UTC).isoformat(),
        "payload": payload,
    }


CANAL_DE: dict[str, Canal] = {
    "order.created": "orders",
    "order.changed": "orders",
    "table.changed": "floor",
    "shift.changed": "cash",
}

"""
La hora que dice el dispositivo, saneada.

Una comanda puede escribirse en una tableta y enviarse minutos despues, cuando
vuelve la red. Para la cocina y para los tiempos de preparacion importa cuando
paso, no cuando llego, asi que el dispositivo manda su propia hora en
`occurred_at` y el servidor la guarda aparte de `created_at`.

El reloj de una tableta no es de fiar: se desconfigura, se queda en la hora de
fabrica, o alguien lo cambia. Aqui se decide cuando creerle.
"""

from datetime import UTC, datetime, timedelta

# Un poco de futuro es normal: los relojes no van sincronizados al segundo.
# Mucho futuro envenena cualquier orden por fecha y pone una comanda de manana
# arriba del tablero de cocina para siempre.
MARGEN_FUTURO = timedelta(minutes=5)

# Mas de dos dias atras ya no es «se envio tarde», es un reloj sin configurar.
# Aceptarlo mandaria la comanda al fondo del tablero, donde nadie la ve.
MARGEN_PASADO = timedelta(days=2)


def resolver(occurred_at: datetime | None, *, ahora: datetime | None = None) -> datetime:
    """
    Devuelve la hora del hecho: la del dispositivo si es creible, la del
    servidor si no.

    NUNCA lanza. Una hora absurda no puede costar una comanda: se descarta el
    dato y se sigue, que es peor para el reporte y mucho mejor para el servicio.
    """
    ahora = ahora or datetime.now(UTC)

    if occurred_at is None:
        return ahora

    # Una hora sin zona no se puede comparar con una que si la tiene. Se asume
    # UTC en vez de rechazarla: es lo que manda un cliente que serializo mal.
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    if occurred_at > ahora + MARGEN_FUTURO:
        return ahora
    if occurred_at < ahora - MARGEN_PASADO:
        return ahora
    return occurred_at

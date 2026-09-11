import { ApiError, NetworkError } from '@/services/http';

/**
 * Lo que se pinta cuando una pantalla no pudo cargar.
 *
 * «No hay red» y «el servidor contesto que no» NO se dicen igual, porque llevan
 * a acciones distintas: lo primero se arregla mirando el router del local, lo
 * segundo no. Si las dos salen como «Error», el encargado no sabe a quien
 * llamar.
 *
 * Y sobre todo: NO se pinta una lista vacia. Un listado sin datos y un listado
 * que no cargo se ven igual, y asi es como un mesero ve «no hay comandas»
 * cuando lo que hay es un cable suelto.
 */
export function AvisoDeFallo({ error }: { error: unknown }) {
  const sinRed = error instanceof NetworkError;
  const texto = sinRed
    ? 'No hay conexion con el servidor. Comprueba la red del local.'
    : error instanceof ApiError
      ? error.message
      : 'No se pudo cargar esta pantalla.';

  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-5 py-4">
      <p className="text-sm font-medium text-destructive">
        {sinRed ? 'Sin conexion' : 'El servidor no respondio'}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">{texto}</p>
    </div>
  );
}

/** Para los `catch` de las pantallas: relanza lo que no es un fallo de la API. */
export function esFalloDeApi(error: unknown): boolean {
  return error instanceof ApiError || error instanceof NetworkError;
}

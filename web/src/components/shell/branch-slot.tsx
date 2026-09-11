import type { Sesion } from '@/lib/auth/session';

/**
 * El hueco del selector de sucursal.
 *
 * Existe desde el primer dia y hoy devuelve `null`. No es codigo muerto: es lo
 * que hace que la interfaz multisucursal sea un componente nuevo y no una
 * refactorizacion.
 *
 * La regla que lo sostiene: LA SUCURSAL ES UNA DIMENSION AMBIENTAL, nunca un
 * parametro de pantalla. Viaja en el token y la resuelve el servidor, asi que
 * ninguna ruta la lleva en el path y ninguna funcion de `services/` la recibe.
 * Cambiar de sucursal sera reemitir la cookie y revalidar — cero cambios en las
 * pantallas que ya existan.
 */
export function HuecoDeSucursal({ sesion }: { sesion: Sesion }) {
  if (sesion.branchIds.length < 2) return null;

  return (
    <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">
      {sesion.branchIds.length} sucursales
    </span>
  );
}

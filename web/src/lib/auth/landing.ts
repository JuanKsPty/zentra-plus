import type { Permiso } from '@/config/permissions';

/**
 * A que pantalla va cada persona al entrar.
 *
 * EL ORDEN IMPORTA y no es alfabetico: alguien puede tener varios de estos
 * permisos y gana el primero que casa.
 *
 * El dueno va primero porque `settings:write` solo lo tiene el administrador.
 * Sin esa linea, un administrador que entra por PIN aterrizaria en el salon
 * —tiene `orders:write` como cualquier mesero— y por correo en el panel: dos
 * puertas, dos destinos, y la sensacion de que el sistema no sabe quien eres.
 *
 * Quien atiende mesas va antes que quien cobra: un encargado que hace las dos
 * cosas empieza el turno de pie, en el salon.
 */
const DESTINOS: readonly { permiso: Permiso; ruta: string }[] = [
  { permiso: 'settings:write', ruta: '/panel' },
  { permiso: 'orders:write', ruta: '/salon' },
  { permiso: 'cash:write', ruta: '/caja' },
  { permiso: 'orders:bump', ruta: '/cocina' },
  { permiso: 'reports:read', ruta: '/panel' },
];

export const DESTINO_POR_DEFECTO = '/panel';

export function destinoPara(permisos: readonly string[] | null | undefined): string {
  const tiene = permisos ?? [];
  return DESTINOS.find((d) => tiene.includes(d.permiso))?.ruta ?? DESTINO_POR_DEFECTO;
}

/**
 * Los permisos, tal como los nombra la API.
 *
 * Espejo de `api/app/core/permissions.py`. Que sea un tipo y no `string` es lo
 * que hace que un permiso mal escrito en la navegacion no compile, en vez de
 * esconder un enlace para siempre sin que nadie sepa por que.
 */

export const PERMISOS = [
  'users:read',
  'users:write',
  'roles:read',
  'roles:write',
  'branches:read',
  'branches:write',
  'branches:read_all',
  'catalog:read',
  'catalog:write',
  'floor:read',
  'floor:write',
  'orders:read',
  'orders:write',
  'orders:bump',
  'cash:read',
  'cash:write',
  'stock:read',
  'stock:write',
  'reports:read',
  'settings:read',
  'settings:write',
] as const;

export type Permiso = (typeof PERMISOS)[number];

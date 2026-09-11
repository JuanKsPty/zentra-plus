import { cookies } from 'next/headers';
import { jwtVerify } from 'jose';

import type { Permiso } from '@/config/permissions';

/**
 * El UNICO sitio del frontend que verifica un JWT.
 *
 * En LoklFlow esta verificacion llego a estar triplicada —middleware, layout y
 * lectura de sesion— y cada copia traia su propio secreto de reserva, que es lo
 * mismo que no verificar: cualquier correccion habia que aplicarla tres veces y
 * el fallback anulaba las tres.
 */

export interface Sesion {
  id: string;
  name: string;
  email: string | null;
  roleName: string | null;
  permissions: Permiso[];
  loginMethod: 'email' | 'pin';
  /** Multisucursal: viaja desde el primer dia, sin interfaz que lo muestre aun. */
  branchId: string;
  branchIds: string[];
}

function secreto(): Uint8Array | null {
  const valor = process.env.JWT_SECRET;
  // Sin valor por defecto, y sin aceptar el de la plantilla: es mejor rechazar
  // toda sesion que validar firmas con un secreto que esta en el repositorio.
  if (!valor || valor.startsWith('cambia-esto')) return null;
  return new TextEncoder().encode(valor);
}

export async function verificarSesion(token: string | undefined): Promise<Sesion | null> {
  const clave = secreto();
  if (!token || !clave) return null;

  try {
    const { payload } = await jwtVerify(token, clave);
    return {
      id: String(payload.sub ?? ''),
      name: String(payload.name ?? ''),
      email: (payload.email as string | null) ?? null,
      roleName: (payload.role_name as string | null) ?? null,
      permissions: (payload.permissions as Permiso[]) ?? [],
      loginMethod: payload.login_method === 'pin' ? 'pin' : 'email',
      branchId: String(payload.branch_id ?? ''),
      branchIds: (payload.branch_ids as string[]) ?? [],
    };
  } catch {
    // Caducado, firmado con otro secreto o manipulado: para el frontend son lo
    // mismo, «no hay sesion». Quien distingue los casos es la API.
    return null;
  }
}

/** La sesion actual, leida en un componente de servidor. */
export async function obtenerSesion(): Promise<Sesion | null> {
  const galletas = await cookies();
  return verificarSesion(galletas.get('access_token')?.value);
}

export function puede(sesion: Sesion | null, permiso: Permiso): boolean {
  return sesion?.permissions.includes(permiso) ?? false;
}

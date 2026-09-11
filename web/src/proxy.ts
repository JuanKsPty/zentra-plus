import { NextResponse, type NextRequest } from 'next/server';

import { verificarSesion } from '@/lib/auth/session';

/**
 * Proteccion de rutas por prefijo.
 *
 * En Next 16 el middleware se llama `proxy.ts`. Comprueba que HAY sesion y que
 * es valida; el PERMISO lo comprueba el layout, porque esto corre en el runtime
 * del borde y no debe conocer el mapa de permisos. Y la autorizacion de verdad
 * la hace siempre la API: esto solo evita pintar una pantalla que va a dar 403.
 */

const PREFIJOS_PROTEGIDOS = ['/panel', '/salon', '/comanda', '/cocina', '/caja', '/mostrador', '/recibo'];

/**
 * Publicos, y declarados aparte y no deducidos.
 *
 * Es blindaje, no redundancia: el dia que alguien anada un prefijo protegido
 * que empiece por `/a`, la pantalla de acceso no puede acabar redirigiendo a si
 * misma. `proxy.spec.ts` lo convierte en un rojo si pasa.
 */
const PREFIJOS_PUBLICOS = ['/acceso'];

export function esPublica(ruta: string): boolean {
  return PREFIJOS_PUBLICOS.some((p) => ruta === p || ruta.startsWith(`${p}/`));
}

export function estaProtegida(ruta: string): boolean {
  if (esPublica(ruta)) return false;
  return PREFIJOS_PROTEGIDOS.some((p) => ruta === p || ruta.startsWith(`${p}/`));
}

export async function proxy(peticion: NextRequest) {
  const ruta = peticion.nextUrl.pathname;
  if (!estaProtegida(ruta)) return NextResponse.next();

  const sesion = await verificarSesion(peticion.cookies.get('access_token')?.value);
  if (sesion) return NextResponse.next();

  const destino = new URL('/acceso', peticion.url);
  // Para volver donde estaba despues de entrar. Solo la ruta, nunca una URL
  // completa: aceptar un destino absoluto convierte esto en un redirector
  // abierto hacia cualquier sitio.
  destino.searchParams.set('volver', ruta);
  return NextResponse.redirect(destino);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|icons/|api|ws).*)'],
};

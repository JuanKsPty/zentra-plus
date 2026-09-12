import { NextResponse, type NextRequest } from 'next/server';

import { verificarSesion } from '@/lib/auth/session';
import { nonceNuevo, politicaDeContenido } from '@/lib/seguridad/cabeceras';

/**
 * Proteccion de rutas por prefijo, y la CSP de cada respuesta.
 *
 * En Next 16 el middleware se llama `proxy.ts`. Comprueba que HAY sesion y que
 * es valida; el PERMISO lo comprueba el layout, porque esto corre en el runtime
 * del borde y no debe conocer el mapa de permisos. Y la autorizacion de verdad
 * la hace siempre la API: esto solo evita pintar una pantalla que va a dar 403.
 *
 * La CSP se pone aqui —y no en `next.config.ts`— porque lleva un `nonce`
 * distinto en cada respuesta. Ver `lib/seguridad/cabeceras.ts`, que es donde
 * esta escrito el por que de cada directiva.
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
  const nonce = nonceNuevo();
  const politica = politicaDeContenido(nonce, process.env.NODE_ENV !== 'production');

  // El nonce viaja en la PETICION por dos caminos, y hacen falta los dos:
  //  - `content-security-policy`, porque es de ahi de donde Next lo saca para
  //    firmar sus propios scripts en linea. Sin esto no hidrata.
  //  - `x-nonce`, para el layout raiz, que se lo pasa a `next-themes`: su
  //    script pone el tema ANTES del primer pintado y no es de Next.
  const cabeceras = new Headers(peticion.headers);
  cabeceras.set('x-nonce', nonce);
  cabeceras.set('content-security-policy', politica);

  const respuesta = await decidir(peticion, cabeceras);
  respuesta.headers.set('content-security-policy', politica);
  return respuesta;
}

async function decidir(peticion: NextRequest, cabeceras: Headers): Promise<NextResponse> {
  const ruta = peticion.nextUrl.pathname;
  const seguir = () => NextResponse.next({ request: { headers: cabeceras } });

  if (!estaProtegida(ruta)) return seguir();

  const sesion = await verificarSesion(peticion.cookies.get('access_token')?.value);
  if (sesion) return seguir();

  const destino = new URL('/acceso', peticion.url);
  // Para volver donde estaba despues de entrar. Solo la ruta, nunca una URL
  // completa: aceptar un destino absoluto convierte esto en un redirector
  // abierto hacia cualquier sitio.
  destino.searchParams.set('volver', ruta);
  return NextResponse.redirect(destino);
}

/**
 * Por donde pasa este middleware.
 *
 * Se excluye `_next` ENTERO y no solo `_next/static` y `_next/image`, ahora que
 * lo que pasa por aqui reescribe cabeceras. Lo que queda dentro son DOCUMENTOS,
 * que son los unicos que necesitan CSP: un `.js`, un `.woff2` o una imagen no
 * ejecutan politica ninguna. Y bajo `_next` vive ademas `_next/hmr`, que es un
 * WebSocket del servidor de desarrollo: un «upgrade» no es sitio donde andar
 * anadiendo cabeceras de respuesta.
 */
export const config = {
  matcher: ['/((?!_next|favicon.ico|icons/|api|ws).*)'],
};

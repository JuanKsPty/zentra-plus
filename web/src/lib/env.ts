/**
 * De donde cuelga la API, que NO es lo mismo en el navegador y en el servidor.
 *
 *  - En el NAVEGADOR la base esta vacia: se pide `/api/...` relativo y el
 *    rewrite de next.config.ts lo lleva a la API. Eso da origen unico, que es
 *    lo que la cookie de sesion (sameSite=strict) necesita para viajar.
 *  - En el SERVIDOR no hay origen del que colgar una ruta relativa, asi que
 *    hace falta una URL absoluta. Dentro de compose la API se llama `api`;
 *    fuera, 127.0.0.1.
 *
 * Next sustituye `process.env.NEXT_PUBLIC_*` al COMPILAR, asi que hay que
 * escribirlo literal: un `process.env[nombre]` con el nombre en una variable no
 * se sustituye y llega como undefined.
 */

const EN_EL_SERVIDOR = typeof window === 'undefined';

export const API_BASE_URL = EN_EL_SERVIDOR
  ? // 127.0.0.1 y no localhost: Node puede resolver ::1 y uvicorn escucha en IPv4.
    (process.env.API_INTERNAL_URL?.trim() || 'http://127.0.0.1:8000')
  : (process.env.NEXT_PUBLIC_API_URL?.trim() ?? '');

export const NOMBRE_PRODUCTO = 'Zentra+';

/**
 * Las cabeceras de seguridad del web, en un solo sitio.
 *
 * Las cuatro fijas las pone `next.config.ts`, porque no dependen de la
 * peticion. La CSP NO puede estar ahi: lleva un `nonce` distinto en cada
 * respuesta y `next.config.ts` se resuelve al compilar. La pone `proxy.ts`, que
 * corre por peticion. Ver el comentario largo de `politicaDeContenido`.
 */

/** Una cabecera tal y como la quiere `headers()` de Next. */
export interface Cabecera {
  key: string;
  value: string;
}

export const CABECERAS_DE_SEGURIDAD: Cabecera[] = [
  // Sin esto, un fichero subido que el servidor sirva como `text/plain` puede
  // acabar ejecutandose como HTML si el navegador «adivina» el tipo.
  { key: 'X-Content-Type-Options', value: 'nosniff' },

  // A un tercero solo le llega el origen, y solo si viene por https. Las rutas
  // de este producto llevan identificadores dentro —`/caja/cuenta/<id>`— y esos
  // no tienen por que salir del local.
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },

  // Redundante con `frame-ancestors 'none'` de la CSP, y se queda: hay
  // navegadores y proxies corporativos que siguen mirando solo esta.
  { key: 'X-Frame-Options', value: 'DENY' },

  // Nada de esto se usa hoy, y lo que no se usa se apaga: una extension
  // inyectada o un script de terceros no puede encender la camara de la tableta
  // de la barra. El dia que el menu por QR necesite la camara, se abre AQUI y
  // se ve en el diff.
  {
    key: 'Permissions-Policy',
    value:
      'accelerometer=(), camera=(), display-capture=(), geolocation=(), gyroscope=(), ' +
      'magnetometer=(), microphone=(), payment=(), usb=()',
  },
];

/**
 * La politica de contenido.
 *
 * POR QUE LLEVA NONCE Y NO ES UNA CADENA FIJA EN next.config.ts
 *
 * Next 16 emite scripts EN LINEA en cada pagina: el arranque de `__next_f` —por
 * donde viaja la carga de los componentes de servidor— y el script de
 * `next-themes`, que pone el tema antes del primer pintado. Se comprobo
 * mirando el HTML servido: tres `<script>` sin `src` hasta en la pagina
 * estatica de acceso.
 *
 * Con `script-src 'self'` a secas, el navegador los bloquea: la aplicacion no
 * hidrata y el tema no se aplica. La salida facil —`'unsafe-inline'`— apaga la
 * CSP para lo unico que de verdad protege, asi que queda descartada. La salida
 * correcta es un nonce distinto por respuesta, y eso obliga a ponerla en el
 * middleware.
 *
 * QUE NECESITA CADA DIRECTIVA, Y POR QUE NO MENOS
 *
 *   script-src  'self' + nonce. Nada de `unsafe-inline`.
 *   style-src   necesita 'unsafe-inline' DE VERDAD, y no por pereza: sonner
 *               inyecta su hoja creando un <style> al vuelo, `next-themes`
 *               inyecta otro para matar las transiciones al cambiar de tema, y
 *               Base UI escribe `style="..."` para colocar los menus. Con
 *               `style-src 'self'` se cae el tema entero. No hay riesgo de
 *               ejecucion aqui: los estilos en linea no corren codigo.
 *   connect-src 'self' BASTA, y esto merece leerse antes de tocarlo: el tiempo
 *               real de este proyecto va por SSE CONTRA EL MISMO ORIGEN
 *               (`EventSource` a `/api/events`, ver lib/realtime/socket.ts). Un
 *               SSE es una respuesta HTTP normal, asi que no aparece ningun
 *               esquema `ws:`/`wss:` por ningun lado. SI ALGUN DIA SE VUELVE AL
 *               WEBSOCKET, ESTA DIRECTIVA TIENE QUE CRECER: `'self'` no es una
 *               promesa de que cualquier transporte al mismo host pase, y el
 *               fallo se ve como «el tablero no se actualiza», sin error de red.
 *   img-src     'self' y `data:` para los SVG en linea de los iconos.
 *   font-src    'self': `next/font` descarga las IBM Plex al compilar y las
 *               sirve desde `/_next/static`. No se habla con Google en
 *               ejecucion, asi que no hay nada que abrir.
 *   frame-ancestors / object-src / base-uri / form-action: cerrados. Ninguno
 *               tiene uso en este producto y los cuatro son agujeros conocidos.
 *
 * NO ESTA `upgrade-insecure-requests` a proposito: el TLS lo termina el borde y
 * una instancia servida por http detras del proxy se quedaria sin subrecursos,
 * sin error visible. Si algun dia el contenedor habla https de punta a punta,
 * ese es el momento de anadirlo.
 *
 * EN DESARROLLO LA POLITICA ES MAS LAXA, Y SOLO AHI
 *
 * Next compila en caliente con `eval` y habla con su propio servidor por
 * WebSocket para recargar. Sin `'unsafe-eval'` y sin `ws:` no hay recarga en
 * caliente y la consola se llena de bloqueos que no existen en produccion.
 */
export function politicaDeContenido(nonce: string, desarrollo: boolean): string {
  const script = ["'self'", `'nonce-${nonce}'`];
  // Turbopack y el refresco de React compilan con `eval` en caliente. No sale
  // de aqui: en produccion no hay ni un `eval` que valga.
  if (desarrollo) script.push("'unsafe-eval'");

  const conectar = ["'self'"];
  // El canal de recarga del servidor de desarrollo. El de la aplicacion es SSE
  // por el mismo origen y no necesita esquema propio.
  if (desarrollo) conectar.push('ws:');

  const directivas: [string, string[]][] = [
    ['default-src', ["'self'"]],
    ['script-src', script],
    ['style-src', ["'self'", "'unsafe-inline'"]],
    ['img-src', ["'self'", 'data:']],
    ['font-src', ["'self'"]],
    ['connect-src', conectar],
    ['manifest-src', ["'self'"]],
    ['worker-src', ["'self'", 'blob:']],
    ['object-src', ["'none'"]],
    ['base-uri', ["'self'"]],
    ['form-action', ["'self'"]],
    ['frame-ancestors', ["'none'"]],
  ];

  return directivas.map(([nombre, valores]) => `${nombre} ${valores.join(' ')}`).join('; ');
}

/**
 * Un nonce nuevo por respuesta.
 *
 * Tiene que ser IMPREDECIBLE: un nonce que se repita o que se pueda adivinar es
 * un `'unsafe-inline'` con pasos de mas. Por eso sale del generador del
 * sistema, que existe igual en el runtime del borde y en Node.
 */
export function nonceNuevo(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes));
}

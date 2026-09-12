import type { NextRequest } from 'next/server';

/**
 * Proxy de /api hacia la API de Zentra+.
 *
 * POR QUE ESTO Y NO UN `rewrite` DE next.config.ts
 * Los rewrites se resuelven al COMPILAR y quedan escritos en el manifiesto de
 * rutas. Con el frontend y la API desplegados por separado eso significa que la
 * imagen del web lleva dentro la direccion de la API del dia que se construyo:
 * cambiar de entorno obligaria a reconstruirla. Aqui el destino se lee en cada
 * peticion, asi que la misma imagen sirve para local, staging y produccion.
 *
 * POR QUE HAY PROXY
 * Para que el navegador vea un UNICO ORIGEN. La cookie de sesion es
 * sameSite=strict y no lleva atributo domain, asi que no viaja si el frontend
 * esta en un host y la API en otro. Con esto el navegador siempre habla con su
 * propio origen y nunca hay CORS que abrir.
 */

export const dynamic = 'force-dynamic';
// El runtime de Node y no el edge: hay que reenviar el cuerpo en streaming.
export const runtime = 'nodejs';

const destino = () => process.env.API_INTERNAL_URL?.trim() || 'http://127.0.0.1:8000';

// Cabeceras que NO se reenvian: las pone la capa de transporte y copiarlas
// rompe la peticion (un `host` del frontend haria que la API se creyera en otro
// sitio; un `content-length` viejo corta el cuerpo).
const NO_SE_REENVIAN = new Set([
  'host',
  'connection',
  'content-length',
  'transfer-encoding',
  'accept-encoding',
]);

async function proxy(request: NextRequest): Promise<Response> {
  const url = new URL(request.url);
  const objetivo = `${destino()}${url.pathname}${url.search}`;

  const cabeceras = new Headers();
  request.headers.forEach((valor, clave) => {
    if (!NO_SE_REENVIAN.has(clave.toLowerCase())) cabeceras.set(clave, valor);
  });

  const conCuerpo = request.method !== 'GET' && request.method !== 'HEAD';

  // EL CUERPO SE LEE ENTERO ANTES DE REENVIARLO, Y NO ES POR COMODIDAD.
  //
  // Esto reenviaba `request.body` en streaming con `duplex: 'half'`. En el Node
  // que este proyecto fija —24, en `.nvmrc` y en el Dockerfile— ESO NO
  // FUNCIONA: `fetch` rechaza con «expected non-null body source» antes de
  // salir a la red, con o sin `cache`, con o sin `redirect`. Y como el rechazo
  // cae en el `catch` de aqui, el navegador recibia un 502 «no hay conexion con
  // el servidor» con la API perfectamente viva y contestando a los GET.
  //
  // Es decir: TODO lo que escribe —entrar, tomar una comanda, cobrar— fallaba
  // desde el navegador, culpando a la red del local. Se encontro levantando el
  // web contra la API de verdad; ni el build ni los tipos lo ven.
  //
  // Leerlo entero cuesta memoria proporcional al cuerpo, y aqui los cuerpos son
  // JSON de una comanda. El dia que haya subida de ficheros hay que volver a
  // esto: la respuesta SI sigue en streaming —el SSE de `/api/events` depende
  // de ello— y lo que habria que resolver es solo la ida.
  const cuerpo = conCuerpo ? await request.arrayBuffer() : undefined;

  let respuesta: Response;
  try {
    respuesta = await fetch(objetivo, {
      method: request.method,
      headers: cabeceras,
      body: cuerpo,
      redirect: 'manual',
      cache: 'no-store',
    });
  } catch {
    // La API no contesta. Se responde con el mismo sobre de error que usa ella,
    // para que el cliente no tenga que distinguir quien fallo.
    return Response.json(
      { error: { code: 'api_inalcanzable', message: 'No hay conexion con el servidor.' } },
      { status: 502 },
    );
  }

  // Se devuelve la respuesta tal cual, cabeceras incluidas: ahi viajan el
  // Set-Cookie de la sesion y el Content-Disposition de las descargas.
  return new Response(respuesta.body, {
    status: respuesta.status,
    statusText: respuesta.statusText,
    headers: respuesta.headers,
  });
}

export {
  proxy as DELETE,
  proxy as GET,
  proxy as PATCH,
  proxy as POST,
  proxy as PUT,
};

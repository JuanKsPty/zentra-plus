import { config as cargarEnv } from 'dotenv';
import type { NextConfig } from 'next';

import { CABECERAS_DE_SEGURIDAD } from './src/lib/seguridad/cabeceras';

// Next solo lee el .env de su propia carpeta, y aqui el .env vive en la RAIZ
// del monorepo para que la API y el frontend no puedan discrepar.
cargarEnv({ path: '../.env', quiet: true });

const nextConfig: NextConfig = {
  // Salida autocontenida: la imagen de produccion es node + esta carpeta, sin
  // node_modules completo.
  output: 'standalone',
  // La raiz del monorepo, para que el trazado de ficheros no se quede corto.
  outputFileTracingRoot: '..',

  // El origen unico NO se resuelve aqui con un rewrite: los rewrites se hornean
  // al compilar y la direccion de la API quedaria dentro de la imagen. Lo hace
  // src/app/api/[...ruta]/route.ts, que lee el destino en cada peticion.

  /**
   * Las cabeceras de seguridad que NO dependen de la peticion.
   *
   * LA CSP NO ESTA AQUI, Y NO ES UN OLVIDO. Next emite scripts en linea en cada
   * pagina —el arranque de `__next_f` y el script del tema—, asi que una CSP
   * sin `'unsafe-inline'` solo funciona con un `nonce`, y un nonce tiene que
   * ser distinto en cada respuesta. `headers()` se resuelve al COMPILAR: aqui
   * solo caben cadenas fijas. La CSP la pone `src/proxy.ts`, que corre por
   * peticion, y las dos salen del mismo modulo:
   * `src/lib/seguridad/cabeceras.ts`.
   *
   * Y se ponen en UN SOLO SITIO cada una a proposito: dos cabeceras
   * `Content-Security-Policy` en la misma respuesta no se suman, se
   * INTERSECAN — el navegador exige las dos a la vez, asi que la de aqui (sin
   * nonce) anularia la del middleware y la aplicacion dejaria de hidratar.
   */
  async headers() {
    return [{ source: '/:ruta*', headers: CABECERAS_DE_SEGURIDAD }];
  },
};

export default nextConfig;

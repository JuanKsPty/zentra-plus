import { config as cargarEnv } from 'dotenv';
import type { NextConfig } from 'next';

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
};

export default nextConfig;

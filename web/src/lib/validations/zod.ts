import { z } from 'zod';

/**
 * Zod, configurado.
 *
 * `jitless` no es una optimizacion: Zod 4 compila los esquemas con
 * `new Function`, y una CSP sin `'unsafe-eval'` lo BLOQUEA. El sintoma es el
 * peor posible — el formulario deja de validar, sin error de red y sin nada
 * visible salvo una linea en una consola que nadie mira.
 *
 * Se arregla activando el modo interpretado, no relajando la politica. El coste
 * es irrelevante: aqui se validan formularios de ocho campos, no lotes de
 * millones de filas.
 *
 * TODOS los esquemas importan `z` de aqui, nunca de 'zod': la configuracion
 * tiene que estar puesta antes de que se construya el primer esquema, y un
 * esquema se construye al importar su archivo.
 */
z.config({ jitless: true });

export { z };

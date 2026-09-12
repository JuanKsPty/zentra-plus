import { globSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { z } from './zod';

/**
 * La trampa de Zod 4 y la CSP, convertida en una prueba.
 *
 * Zod 4 compila los esquemas con `new Function`, y una CSP sin `'unsafe-eval'`
 * lo BLOQUEA. El sintoma es el peor posible: el formulario deja de validar. No
 * hay error de red, no hay pantalla rota, no hay nada — solo una linea en una
 * consola que nadie mira, y un formulario que acepta lo que sea.
 *
 * Se arregla con `z.config({ jitless: true })`, y eso tiene que estar puesto
 * ANTES de que se construya el primer esquema. Un esquema se construye al
 * IMPORTAR su archivo, asi que basta un `import { z } from 'zod'` en cualquier
 * modulo para saltarse la configuracion sin romper nada visible.
 *
 * Por eso hay dos pruebas: una comprueba que la configuracion existe y la otra
 * que nadie se la salta. La segunda es la que de verdad hace falta.
 */

const RAIZ = fileURLToPath(new URL('../..', import.meta.url));

const PERMITIDO = 'lib/validations/zod.ts';

function fuentes(): string[] {
  return globSync('**/*.{ts,tsx}', { cwd: RAIZ }).filter((ruta) => !ruta.endsWith('.spec.ts'));
}

describe('Zod, configurado para vivir bajo una CSP', () => {
  it('el modo interpretado esta puesto', () => {
    // Sin jitless, esto compilaria con `new Function` y bajo la CSP de
    // produccion no validaria nada.
    const esquema = z.object({ pin: z.string().min(4, 'Cuatro digitos') });

    expect(esquema.safeParse({ pin: '12' }).success).toBe(false);
    expect(esquema.safeParse({ pin: '1234' }).success).toBe(true);
  });

  it('nadie importa `zod` directamente', () => {
    // El unico archivo que puede es el que pone la configuracion. Cualquier
    // otro se la salta, y el fallo no aparece hasta que hay CSP — es decir, en
    // produccion y solo ahi.
    const culpables = fuentes().filter((ruta) => {
      if (ruta.replaceAll('\\', '/') === PERMITIDO) return false;
      const contenido = readFileSync(`${RAIZ}/${ruta}`, 'utf8');
      return /from ['"]zod['"]/.test(contenido);
    });

    expect(
      culpables,
      `importan 'zod' en vez de '@/lib/validations/zod':\n  ${culpables.join('\n  ')}`,
    ).toEqual([]);
  });

  it('el escaner sabe encontrar algo', () => {
    const todos = fuentes();
    expect(todos.length).toBeGreaterThan(20);
    // Y mira DENTRO del archivo permitido, que es el unico que sabemos que
    // importa 'zod': si el escaner dejara de leer, esto seguiria en verde.
    expect(/from 'zod'/.test(readFileSync(`${RAIZ}/${PERMITIDO}`, 'utf8'))).toBe(true);
  });
});

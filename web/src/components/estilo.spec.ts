import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { globSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

/**
 * Dos reglas del sistema de diseno que se vigilan leyendo el codigo fuente.
 *
 * Se lee y no se renderiza porque jsdom NO aplica Tailwind: una asercion sobre
 * medidas reales devolveria ceros y pasaria siempre. Y porque el fallo que
 * buscan no tiene sintoma en una pantalla — tiene sintoma en OTRA pantalla, o
 * en otro ancho, o de noche.
 */

const RAIZ = fileURLToPath(new URL('..', import.meta.url));

// `components/ui` es codigo generado por el CLI de shadcn: se parchea a mano
// solo en la densidad, y linear su paleta seria pelearse con cada actualizacion.
const EXCLUIDOS = ['components/ui/'];

function archivos(patron: string): string[] {
  return globSync(patron, { cwd: RAIZ })
    .filter((ruta) => !EXCLUIDOS.some((excluido) => ruta.includes(excluido)))
    .filter((ruta) => !ruta.endsWith('.spec.ts') && !ruta.endsWith('.spec.tsx'));
}

function buscar(patron: string, expresion: RegExp): string[] {
  const hallazgos: string[] = [];
  for (const ruta of archivos(patron)) {
    const contenido = readFileSync(`${RAIZ}/${ruta}`, 'utf8');
    contenido.split('\n').forEach((linea, indice) => {
      const encontrado = linea.match(expresion);
      if (encontrado) hallazgos.push(`${ruta}:${indice + 1}  ${encontrado[0]}`);
    });
  }
  return hallazgos;
}

const SM_ASCENDENTE = /(?<!max-)\bsm:(h|size|min-h|w|px|py|text)-/;

const PALETA_CRUDA = new RegExp(
  '\\b(bg|text|border|ring|fill|stroke|from|to|via|divide|placeholder)-' +
    '(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|' +
    'sky|blue|indigo|violet|purple|fuchsia|pink|rose)-\\d{2,3}\\b' +
    '|\\bbg-white\\b|\\bbg-black\\b',
);

describe('el sistema de diseno se respeta', () => {
  it('no hay colores crudos de Tailwind fuera de las primitivas', () => {
    // Un solo `bg-white` en una pantalla operativa es un rectangulo cegador en
    // una cocina de noche, y no se encuentra revisando: se encuentra de noche.
    const culpables = buscar('**/*.tsx', PALETA_CRUDA);

    expect(culpables, `usa la paleta cruda:\n  ${culpables.join('\n  ')}`).toEqual([]);
  });

  it('ninguna clase de geometria usa el prefijo sm: ascendente', () => {
    // Ver button.spec.ts: con `h-11 sm:h-8`, un className del sitio de llamada
    // encoge el control EN ESCRITORIO sin que nadie lo note.
    //
    // El `(?<!max-)` no es adorno: sin el, `\bsm:` casa DENTRO de `max-sm:`
    // —hay limite de palabra entre el guion y la ese— y el escaner marcaria
    // como error justo la forma correcta. Lo destapo el centinela de abajo.
    const culpables = buscar('**/*.tsx', SM_ASCENDENTE);

    expect(culpables, `usa sm: ascendente:\n  ${culpables.join('\n  ')}`).toEqual([]);
  });

  it('el escaner sabe encontrar algo', () => {
    // Un guardian que solo sabe decir «no encontre nada» sigue en verde el dia
    // que deja de mirar. Esto ancla que los patrones funcionan.
    expect(PALETA_CRUDA.test('className="bg-gray-50 p-4"')).toBe(true);
    expect(PALETA_CRUDA.test('className="bg-white"')).toBe(true);
    expect(PALETA_CRUDA.test('className="bg-card text-muted-foreground"')).toBe(false);
    expect(SM_ASCENDENTE.test('className="h-11 sm:h-8"')).toBe(true);
    expect(SM_ASCENDENTE.test('className="h-8 max-sm:h-11"')).toBe(false);
    expect(archivos('**/*.tsx').length).toBeGreaterThan(0);
  });
});

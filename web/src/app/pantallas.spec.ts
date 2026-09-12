import { globSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

/**
 * Tres reglas de las pantallas, vigiladas leyendo el codigo fuente.
 *
 * Se leen y no se renderizan porque los tres fallos que buscan NO TIENEN
 * SINTOMA en la pantalla que los comete: las tres formas de mentir se ven
 * exactamente igual que el caso bueno.
 *
 *   1. Una lista vacia y una lista que no cargo se ven igual. «No hay comandas»
 *      manda a esperar; «no pudimos preguntar» manda a mirar el router.
 *   2. Un `notFound()` en un `catch` generico convierte un corte de red en «eso
 *      no existe», y quien lo lee cierra la pestana en vez de avisar.
 *   3. El aviso de vacio (`SinNada`) dentro de un `catch` es la primera regla
 *      otra vez, pero escrita a mano y con mejor pinta.
 *
 * Y se vigila con un escaner, no con una revision, porque la regla se rompe al
 * ANADIR una pantalla —cuando nadie esta mirando esta— y porque la pantalla
 * nueva casi siempre se escribe copiando una vieja.
 */

const RAIZ_APP = fileURLToPath(new URL('.', import.meta.url));

interface Pantalla {
  ruta: string;
  fuente: string;
}

function pantallas(): Pantalla[] {
  return globSync('**/page.tsx', { cwd: RAIZ_APP })
    .sort()
    .map((ruta) => ({ ruta, fuente: readFileSync(`${RAIZ_APP}/${ruta}`, 'utf8') }));
}

/** Una pantalla que habla con la API es una pantalla que puede no cargar. */
function cargaDatos(fuente: string): boolean {
  return /from '@\/services\//.test(fuente);
}

/**
 * El cuerpo de cada `catch` del archivo.
 *
 * Cuenta llaves desde la que abre el bloque. Es suficiente aqui —el JSX y las
 * plantillas de este proyecto estan balanceados— y no hace falta un parser para
 * responder «¿que hay dentro de este catch?».
 */
function cuerposDeCatch(fuente: string): string[] {
  const cuerpos: string[] = [];
  const busqueda = /\bcatch\b[^{]*\{/g;

  let encontrado: RegExpExecArray | null;
  while ((encontrado = busqueda.exec(fuente)) !== null) {
    let profundidad = 1;
    let indice = encontrado.index + encontrado[0].length;
    const inicio = indice;

    while (indice < fuente.length && profundidad > 0) {
      const caracter = fuente[indice];
      if (caracter === '{') profundidad++;
      else if (caracter === '}') profundidad--;
      indice++;
    }

    cuerpos.push(fuente.slice(inicio, indice - 1));
  }

  return cuerpos;
}

describe('las pantallas no mienten cuando la API no responde', () => {
  it('toda pantalla que carga datos sabe decir que no pudo cargarlos', () => {
    // Sin `AvisoDeFallo`, lo que queda es un listado vacio o una pantalla en
    // blanco, y las dos se leen como «aqui no hay nada».
    const mudas = pantallas()
      .filter(({ fuente }) => cargaDatos(fuente) && !fuente.includes('AvisoDeFallo'))
      .map(({ ruta }) => ruta);

    expect(mudas, `cargan datos y no avisan del fallo:\n  ${mudas.join('\n  ')}`).toEqual([]);
  });

  it('«no existe» solo se dice cuando la API contesta 404', () => {
    // `notFound()` en un `catch` generico es la mentira mas cara de las tres:
    // convierte «la API esta caida» en «eso no existe», y contra eso no hay
    // nada que hacer salvo irse.
    const culpables = pantallas()
      .flatMap(({ ruta, fuente }) =>
        cuerposDeCatch(fuente)
          .filter((cuerpo) => /\bnotFound\s*\(/.test(cuerpo) && !/\b404\b/.test(cuerpo))
          .map(() => ruta),
      );

    expect(culpables, `notFound() sin comprobar el 404:\n  ${culpables.join('\n  ')}`).toEqual([]);
  });

  it('el aviso de «no hay nada» no se usa para tapar un fallo', () => {
    const culpables = pantallas().flatMap(({ ruta, fuente }) =>
      cuerposDeCatch(fuente)
        .filter((cuerpo) => /\bSinNada\b/.test(cuerpo))
        .map(() => ruta),
    );

    expect(culpables, `pintan vacio tras un fallo:\n  ${culpables.join('\n  ')}`).toEqual([]);
  });

  it('el escaner sabe encontrar algo', () => {
    // Un guardian que solo sabe decir «no encontre nada» sigue en verde el dia
    // que deja de mirar.
    const todas = pantallas();
    expect(todas.length).toBeGreaterThan(5);
    expect(todas.filter(({ fuente }) => cargaDatos(fuente)).length).toBeGreaterThan(5);

    const falsa = `
      try { await x(); } catch (error) {
        if (algo) notFound();
        return <SinNada titulo="Nada" />;
      }
    `;
    const cuerpo = cuerposDeCatch(falsa)[0] ?? '';
    expect(cuerpo).toContain('notFound()');
    expect(cuerpo).toContain('SinNada');
    expect(/\b404\b/.test(cuerpo)).toBe(false);

    // Y que el contador de llaves no se coma el `catch` entero por un JSX con
    // llaves dentro.
    const conJsx = `try { a(); } catch (e) { return <p>{e.message}</p>; } finally { b(); }`;
    expect(cuerposDeCatch(conJsx)[0]).toContain('e.message');
    expect(cuerposDeCatch(conJsx)[0]).not.toContain('finally');
  });
});

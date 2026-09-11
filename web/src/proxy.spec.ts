import { describe, expect, it } from 'vitest';

import { esPublica, estaProtegida } from './proxy';

describe('la proteccion por prefijo', () => {
  it('protege las superficies operativas y el panel', () => {
    for (const ruta of ['/panel', '/panel/catalogo', '/salon', '/caja/cuenta/1', '/cocina']) {
      expect(estaProtegida(ruta), ruta).toBe(true);
    }
  });

  it('deja pasar las publicas', () => {
    for (const ruta of ['/', '/acceso', '/acceso/pin', '/acceso/pin/abc']) {
      expect(estaProtegida(ruta), ruta).toBe(false);
    }
  });

  it('«/acceso» no puede quedar protegida por un prefijo parecido', () => {
    // El dia que alguien anada un prefijo protegido que empiece por `/a`, la
    // pantalla de acceso acabaria redirigiendo a si misma: un bucle que en el
    // navegador se ve como «la pagina no carga», sin ningun error.
    expect(esPublica('/acceso')).toBe(true);
    expect(estaProtegida('/acceso')).toBe(false);
  });

  it('un prefijo no captura rutas que solo empiezan igual', () => {
    // `/paneles` no es `/panel`.
    expect(estaProtegida('/paneles')).toBe(false);
    expect(estaProtegida('/cajero')).toBe(false);
  });
});

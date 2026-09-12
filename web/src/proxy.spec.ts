import { describe, expect, it } from 'vitest';

import { config, esPublica, estaProtegida } from './proxy';

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

describe('por donde pasa el middleware', () => {
  // Se lee el matcher REAL del archivo, no una copia: una copia se queda vieja
  // justo el dia que alguien cambia el original.
  const atraviesa = (ruta: string) => new RegExp(`^${config.matcher[0]}$`).test(ruta);

  it('las interioridades de Next se quedan fuera', () => {
    // Excluir solo `_next/static` y `_next/image` deja dentro `_next/hmr`, que
    // es el WebSocket del servidor de desarrollo. Ahora que el middleware
    // reescribe cabeceras, un «upgrade» no es sitio por donde hacerlo pasar —y
    // ninguno de estos es un documento, asi que la CSP no les hace nada.
    expect(atraviesa('/_next/hmr')).toBe(false);
    expect(atraviesa('/_next/static/chunks/main.js')).toBe(false);
    expect(atraviesa('/_next/image')).toBe(false);
  });

  it('la API no lleva CSP: no es un documento', () => {
    expect(atraviesa('/api/orders')).toBe(false);
    expect(atraviesa('/api/events')).toBe(false);
  });

  it('las pantallas si pasan, que es donde la politica sirve de algo', () => {
    for (const ruta of ['/', '/acceso', '/salon', '/panel/catalogo', '/caja/cuenta/1']) {
      expect(atraviesa(ruta), ruta).toBe(true);
    }
  });
});

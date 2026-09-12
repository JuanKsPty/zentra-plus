import { describe, expect, it } from 'vitest';

import { CABECERAS_DE_SEGURIDAD, nonceNuevo, politicaDeContenido } from './cabeceras';

/**
 * La CSP se prueba leyendola, porque sus dos fallos NO TIENEN SINTOMA DONDE SE
 * MIRA: el build pasa igual, el servidor responde 200 igual, y lo que se rompe
 * —la hidratacion, la validacion de un formulario— solo se ve en la consola del
 * navegador, que en una tableta de la barra no mira nadie.
 *
 * Lo que se ancla aqui no es el texto de la politica, es cada decision que se
 * puede deshacer sin darse cuenta: relajar `script-src`, quitar el
 * `'unsafe-inline'` que los estilos SI necesitan, o dejar que lo de desarrollo
 * se cuele en produccion.
 */

function directiva(politica: string, nombre: string): string[] {
  const parte = politica
    .split(';')
    .map((trozo) => trozo.trim())
    .find((trozo) => trozo === nombre || trozo.startsWith(`${nombre} `));

  return parte ? parte.split(/\s+/).slice(1) : [];
}

const produccion = politicaDeContenido('ABC123', false);
const desarrollo = politicaDeContenido('ABC123', true);

describe('la politica de contenido', () => {
  it('los scripts van con nonce, y nunca con unsafe-inline', () => {
    // `'unsafe-inline'` en `script-src` apaga la CSP para lo unico que de
    // verdad protege. Y si alguien lo anade «solo para que compile», el nonce
    // deja de tener efecto: un navegador que ve un nonce IGNORA unsafe-inline,
    // asi que la mezcla no avisa de nada.
    expect(directiva(produccion, 'script-src')).toEqual(["'self'", "'nonce-ABC123'"]);
    expect(produccion).not.toContain("script-src 'self' 'unsafe-inline'");
    expect(directiva(produccion, 'script-src')).not.toContain("'unsafe-inline'");
    expect(directiva(produccion, 'script-src')).not.toContain("'unsafe-eval'");
  });

  it('los estilos en linea SI se permiten, y esto no es un descuido', () => {
    // sonner inyecta su hoja creando un <style>, `next-themes` inyecta otro
    // para matar las transiciones al cambiar de tema, y Base UI escribe
    // `style="..."` para colocar los menus. Con `style-src 'self'` se cae el
    // tema entero, y no hay riesgo de ejecucion: un estilo no corre codigo.
    expect(directiva(produccion, 'style-src')).toContain("'unsafe-inline'");
  });

  it('connect-src es «self» porque el tiempo real va por SSE del mismo origen', () => {
    // Si algun dia se vuelve al WebSocket, esta prueba tiene que cambiar A LA
    // VEZ que la politica. El fallo de no hacerlo se ve como «el tablero no se
    // actualiza», sin error de red y sin nada en el servidor.
    expect(directiva(produccion, 'connect-src')).toEqual(["'self'"]);
  });

  it('lo que no se usa esta cerrado', () => {
    expect(directiva(produccion, 'object-src')).toEqual(["'none'"]);
    expect(directiva(produccion, 'frame-ancestors')).toEqual(["'none'"]);
    expect(directiva(produccion, 'base-uri')).toEqual(["'self'"]);
    expect(directiva(produccion, 'form-action')).toEqual(["'self'"]);
    expect(directiva(produccion, 'default-src')).toEqual(["'self'"]);
  });

  it('las fuentes son propias: no se habla con Google en ejecucion', () => {
    // `next/font` descarga las IBM Plex al compilar. Si alguna vez aparece un
    // dominio aqui, es que alguien volvio a enlazar la hoja de Google y la
    // tipografia dejo de cargar cuando el local se queda sin internet.
    expect(directiva(produccion, 'font-src')).toEqual(["'self'"]);
  });

  it('lo laxo de desarrollo NO se cuela en produccion', () => {
    // Next compila en caliente con `eval` y recarga por WebSocket. Las dos
    // cosas se abren solo en desarrollo, y esta prueba es lo que impide que el
    // dia que una de ellas moleste alguien la abra «un momentito» en las dos.
    expect(directiva(desarrollo, 'script-src')).toContain("'unsafe-eval'");
    expect(directiva(desarrollo, 'connect-src')).toContain('ws:');

    expect(directiva(produccion, 'script-src')).not.toContain("'unsafe-eval'");
    expect(directiva(produccion, 'connect-src')).not.toContain('ws:');
  });

  it('el nonce es distinto en cada respuesta', () => {
    // Un nonce que se repite es un `'unsafe-inline'` con pasos de mas.
    const unos = new Set(Array.from({ length: 50 }, () => nonceNuevo()));
    expect(unos.size).toBe(50);
    // Y tiene que caber en la cabecera sin comillas raras: base64 puro.
    expect([...unos].every((valor) => /^[A-Za-z0-9+/=]+$/.test(valor))).toBe(true);
  });
});

describe('las cabeceras fijas', () => {
  it('estan las cuatro que no dependen de la peticion', () => {
    const nombres = CABECERAS_DE_SEGURIDAD.map((cabecera) => cabecera.key);
    expect(nombres).toEqual([
      'X-Content-Type-Options',
      'Referrer-Policy',
      'X-Frame-Options',
      'Permissions-Policy',
    ]);
  });

  it('la camara y el microfono estan apagados', () => {
    // La tableta de la barra tiene camara. Nada de esta aplicacion la usa, y lo
    // que no se usa se apaga: el dia que el menu por QR la necesite, se abre y
    // se ve en el diff.
    const permisos = CABECERAS_DE_SEGURIDAD.find((c) => c.key === 'Permissions-Policy')?.value;
    expect(permisos).toContain('camera=()');
    expect(permisos).toContain('microphone=()');
    expect(permisos).toContain('geolocation=()');
  });

  it('ninguna cabecera fija es la CSP', () => {
    // Dos cabeceras `Content-Security-Policy` en la misma respuesta no se
    // suman: se INTERSECAN. Una aqui (sin nonce) anularia la del middleware y
    // la aplicacion dejaria de hidratar, en produccion y solo ahi.
    const nombres = CABECERAS_DE_SEGURIDAD.map((c) => c.key.toLowerCase());
    expect(nombres).not.toContain('content-security-policy');
  });
});

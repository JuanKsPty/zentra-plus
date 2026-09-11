import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { PERMISOS } from '@/config/permissions';

import { DESTINOS, destinosDeBarraPara, destinosPara, esDestinoActivo } from './navigation';

const RAIZ_APP = fileURLToPath(new URL('../app', import.meta.url));

describe('la navegacion del panel', () => {
  it('todo destino declara un permiso que existe', () => {
    // Si no, el enlace se esconde para siempre y nadie relaciona el sintoma
    // («no me aparece Catalogo») con un typo en una lista.
    for (const destino of DESTINOS) {
      expect(PERMISOS, destino.id).toContain(destino.permiso);
    }
  });

  it('no se ofrece nada que no se pueda abrir', () => {
    expect(destinosPara([]).map((d) => d.id)).toEqual([]);
    expect(destinosPara(['reports:read']).map((d) => d.id)).toEqual(['resumen']);
  });

  it('en la barra del pulgar caben cuatro, y solo los que se pueden abrir', () => {
    // El quinto hueco es «Mas»: meter cinco deja el cajon sin puerta.
    const todos = destinosDeBarraPara(PERMISOS);
    expect(todos.length).toBeLessThanOrEqual(4);
    expect(todos.map((d) => d.barra)).toEqual([...todos.map((d) => d.barra)].sort());

    expect(destinosDeBarraPara([]).map((d) => d.id)).toEqual([]);
  });

  it('«Resumen» no se queda encendido en todas partes', () => {
    // `/panel` es prefijo de todo lo demas. Sin la excepcion, la barra deja de
    // decir donde estas.
    expect(esDestinoActivo('/panel', '/panel')).toBe(true);
    expect(esDestinoActivo('/panel', '/panel/catalogo')).toBe(false);
    expect(esDestinoActivo('/panel/catalogo', '/panel/catalogo/productos/nuevo')).toBe(true);
  });

  it('cada destino apunta a una carpeta que existe', () => {
    // Un enlace a una ruta que nadie creo es un 404 que solo se descubre
    // pulsandolo, y la lista crece antes que las pantallas.
    const rotos = DESTINOS.filter((destino) => {
      const carpeta = `${RAIZ_APP}/(panel)${destino.href}`;
      return !existsSync(carpeta);
    }).map((d) => `${d.id} -> ${d.href}`);

    expect(rotos, `enlaces sin pantalla:\n  ${rotos.join('\n  ')}`).toEqual([]);
  });
});

import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

import { DESTINOS, DESTINOS_PREVISTOS, destinoPara } from './landing';

const RAIZ_APP = fileURLToPath(new URL('../../app', import.meta.url));

// Las pantallas viven en grupos de ruta, que no aparecen en la URL.
const GRUPOS = ['(panel)', '(operacion)', ''];

const existeLaPantalla = (ruta: string) =>
  GRUPOS.some((grupo) => existsSync(`${RAIZ_APP}/${grupo}${ruta}`));

describe('el aterrizaje por rol', () => {
  it('el dueno va al panel aunque tambien pueda tomar comandas', () => {
    // El caso que justifica el orden: un administrador tiene `orders:write`
    // como cualquier mesero. Sin poner `settings:write` primero, entraria al
    // salon por PIN y al panel por correo — dos puertas, dos destinos.
    const dueno = ['settings:write', 'orders:write', 'cash:write', 'reports:read'];

    expect(destinoPara(dueno, DESTINOS_PREVISTOS)).toBe('/panel');
  });

  it('quien atiende mesas empieza de pie, en el salon', () => {
    expect(destinoPara(['orders:write', 'cash:write'], DESTINOS_PREVISTOS)).toBe('/salon');
  });

  it('la cocina va a su tablero', () => {
    expect(destinoPara(['orders:bump'], DESTINOS_PREVISTOS)).toBe('/cocina');
  });

  it('sin ningun permiso conocido, al panel', () => {
    expect(destinoPara([])).toBe('/panel');
    expect(destinoPara(null)).toBe('/panel');
  });

  it('nadie aterriza en una pantalla que no existe', () => {
    // Aterrizar a alguien en un 404 nada mas entrar es peor que aterrizarlo en
    // un panel con poco contenido. Los destinos previstos se van moviendo a
    // DESTINOS segun se construyen sus pantallas.
    const rotos = DESTINOS.filter((d) => !existeLaPantalla(d.ruta)).map((d) => d.ruta);

    expect(rotos, `destinos sin pantalla: ${rotos.join(', ')}`).toEqual([]);
  });
});

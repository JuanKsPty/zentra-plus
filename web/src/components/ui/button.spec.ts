import { describe, expect, it } from 'vitest';

import { cn } from '@/lib/utils';

import { buttonVariants } from './button';

const clases = (opciones: Parameters<typeof buttonVariants>[0]) =>
  buttonVariants(opciones).split(/\s+/);

const TAMANOS = ['default', 'sm', 'lg', 'touch', 'key'] as const;
const ICONOS = ['icon', 'icon-sm', 'icon-lg', 'icon-touch', 'icon-key'] as const;

describe('la densidad de los botones', () => {
  it('la altura de escritorio nunca va detras de un prefijo', () => {
    // ESTA es la invariante. `tailwind-merge` no ve conflicto entre `h-12` y
    // `sm:h-8` —son modificadores distintos— pero si entre `h-12` y `h-8`. Con
    // la forma ascendente (`h-11 sm:h-8`), un `className="h-12"` del sitio de
    // llamada dejaria `h-12 sm:h-8` y el boton encogeria A 32 px EN ESCRITORIO.
    // Con el valor de escritorio sin prefijo, lo pisa como cualquier otra clase.
    for (const size of TAMANOS) {
      expect(clases({ size }).some((c) => /^h-\d/.test(c)), `size=${size}`).toBe(true);
    }
    for (const size of ICONOS) {
      expect(clases({ size }).some((c) => /^size-\d/.test(c)), `size=${size}`).toBe(true);
    }
  });

  it('nunca se usa el prefijo sm: ascendente para la geometria', () => {
    for (const size of [...TAMANOS, ...ICONOS]) {
      const ascendentes = clases({ size }).filter((c) => /^sm:(h|size|px|text)-/.test(c));
      expect(ascendentes, `size=${size}`).toEqual([]);
    }
  });

  it('en movil todo llega al suelo tactil de 44 px', () => {
    // 44 px es h-11. Los tamanos compactos del panel se suben con max-sm:.
    for (const size of ['default', 'lg'] as const) {
      expect(clases({ size })).toContain('max-sm:h-11');
    }
    expect(clases({ size: 'icon' })).toContain('max-sm:size-11');
  });

  it('touch mide 44 px y key 56 px, a cualquier ancho', () => {
    // Sin max-sm: a proposito: marcan lo que se pulsa de pie, y eso no cambia
    // porque la pantalla sea grande.
    expect(clases({ size: 'touch' })).toContain('h-11');
    expect(clases({ size: 'key' })).toContain('h-14');
    expect(clases({ size: 'touch' }).some((c) => c.startsWith('max-sm:h-'))).toBe(false);
    expect(clases({ size: 'key' }).some((c) => c.startsWith('max-sm:h-'))).toBe(false);
  });

  it('un className del sitio de llamada pisa la altura, no se acumula', () => {
    // La comprobacion de verdad, y se hace sobre `cn(...)` y no sobre `cva`
    // porque `cva` solo concatena: quien resuelve el conflicto es
    // `tailwind-merge`, dentro de `cn`, que es exactamente lo que hace el
    // componente. Probar la capa de abajo daria un falso rojo.
    const resultado = cn(buttonVariants({ size: 'default', className: 'h-12' })).split(/\s+/);

    expect(resultado).toContain('h-12');
    expect(resultado).not.toContain('h-8');
    // Y el valor de movil sobrevive, que es lo que se quiere: quien pide una
    // altura concreta la pide para escritorio.
    expect(resultado).toContain('max-sm:h-11');
  });

  it('con la forma ascendente, un className NO pisaria el escritorio', () => {
    // El contraejemplo, escrito para que la razon de la regla no se pierda.
    // `tailwind-merge` ve `h-12` y `sm:h-8` como modificadores distintos, asi
    // que los deja convivir: en escritorio ganaria `sm:h-8` y el boton
    // encogeria a 32 px. Si algun dia esto empieza a fallar, es que
    // tailwind-merge cambio de criterio y la regla se puede revisar.
    const ascendente = cn('h-11 sm:h-8', 'h-12').split(/\s+/);

    expect(ascendente).toContain('h-12');
    expect(ascendente).toContain('sm:h-8');
  });
});

import { describe, expect, it } from 'vitest';

import { deLaApi, formatearDinero, paraLaApi } from './money';

describe('el dinero en el navegador', () => {
  it('entra como cadena y se guarda en centavos enteros', () => {
    // La API manda "12.50" y no 12.5 a proposito: un numero JSON lo parsea el
    // navegador como coma flotante.
    expect(deLaApi('12.50')).toBe(1250);
    expect(deLaApi('0.05')).toBe(5);
    expect(deLaApi('1000.00')).toBe(100000);
  });

  it('sumar precios en centavos es exacto', () => {
    // Lo que en coma flotante no lo es: 0.1 + 0.2 !== 0.3.
    const total = deLaApi('0.10') + deLaApi('0.20');

    expect(total).toBe(30);
    expect(paraLaApi(total)).toBe('0.30');
    expect(0.1 + 0.2).not.toBe(0.3);
  });

  it('la ida y vuelta conserva el valor', () => {
    for (const valor of ['0.00', '0.01', '2.50', '19.99', '1234.56']) {
      expect(paraLaApi(deLaApi(valor))).toBe(valor);
    }
  });

  it('se formatea para quien lo lee', () => {
    expect(formatearDinero(250)).toContain('2.50');
  });
});

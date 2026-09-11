/**
 * El dinero, en el navegador.
 *
 * La API manda los importes como CADENA —Pydantic serializa `Decimal` asi— y no
 * como numero, a proposito: un numero JSON lo parsea el navegador como coma
 * flotante y a partir de ahi sumar dos precios ya no es exacto.
 *
 * Aqui se convierte a CENTAVOS ENTEROS en cuanto entra, y toda la aritmetica
 * del cliente trabaja con enteros. `deLaApi` es el unico sitio que parsea.
 *
 * Ojo: lo que el cliente calcula son PREVISUALIZACIONES —el restante de un pago
 * dividido, el cambio—. Todo total autoritativo lo calcula el servidor.
 */

/** `"12.50"` -> `1250`. Redondea al centavo, que es la unidad minima de cobro. */
export function deLaApi(valor: string | number): number {
  return Math.round(Number(valor) * 100);
}

/** `1250` -> `"12.50"`, para mandarlo de vuelta. */
export function paraLaApi(centavos: number): string {
  return (centavos / 100).toFixed(2);
}

export function formatearDinero(centavos: number, moneda = 'USD', local = 'es-PA'): string {
  return new Intl.NumberFormat(local, { style: 'currency', currency: moneda }).format(
    centavos / 100,
  );
}

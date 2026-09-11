/**
 * El contrato con la API.
 *
 * Los DTO son lo que devuelve la API tal cual: snake_case y fechas como cadena.
 * Los modelos de dominio son lo que consume la interfaz: camelCase y Date.
 * La conversion vive en services/, nunca en un componente.
 *
 * Cuando el esquema crezca, estos DTO se generaran desde el openapi.json que
 * FastAPI ya publica, para que renombrar un campo en Python sea un error de
 * compilacion aqui en vez de un undefined en pantalla.
 */

/** El sobre de error de la API. Toda respuesta que no sea 2xx llega asi. */
export interface ErrorDto {
  error: {
    code: string;
    message: string;
    details: { field: string | null; message: string }[];
    request_id: string | null;
  };
}

export interface SaludDto {
  status: string;
  app: string;
  version: string;
  environment: string;
}

export interface Salud {
  status: string;
  app: string;
  version: string;
  environment: string;
}

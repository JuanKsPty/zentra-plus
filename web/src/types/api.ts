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

/**
 * La forma de todo listado. Una sola convencion en toda la API.
 *
 * `total` no es decoracion: es lo que permite que una pantalla diga «mostrando
 * 50 de 312» en vez de cortar en silencio, que se lee como «esto es todo».
 */
export interface PaginaDto<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
  has_more: boolean;
}

export interface Pagina<T> {
  items: T[];
  page: number;
  size: number;
  total: number;
  hasMore: boolean;
}

export interface UsuarioDto {
  id: string;
  name: string;
  email: string | null;
  is_active: boolean;
  role_id?: string | null;
  role_name?: string | null;
}

/** Lo minimo para pintar la rejilla del teclado de PIN. Publico, sin correo. */
export interface UsuarioOperativoDto {
  id: string;
  name: string;
  role_name: string | null;
}

export interface CategoriaDto {
  id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
}

export interface ProductoDto {
  id: string;
  name: string;
  description: string | null;
  price: string;
  station: string;
  image_url: string | null;
  is_active: boolean;
  category_id: string | null;
  /** Ya resuelto para la sucursal de la peticion. Quien consume esto no tiene
   *  que saber que existe una tabla de overrides. */
  effective_price: string;
  is_available: boolean;
}

export interface SectorDto {
  id: string;
  name: string;
  sort_order: number;
  is_active: boolean;
}

export interface MesaDto {
  id: string;
  number: number;
  capacity: number;
  shape: string;
  position_x: number | null;
  position_y: number | null;
  is_active: boolean;
  sector_id: string;
  status: string;
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

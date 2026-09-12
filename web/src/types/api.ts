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

export interface LineaDto {
  id: string;
  product_id: string;
  product_name: string;
  unit_price: string;
  station: string;
  quantity: number;
  subtotal: string;
  notes: string | null;
  status: string;
}

export interface ComandaDto {
  id: string;
  order_number: number;
  label: string | null;
  table_id: string | null;
  table_number: number | null;
  waiter_id: string | null;
  source: string;
  status: string;
  notes: string | null;
  subtotal: string;
  tip_amount: string;
  total: string;
  occurred_at: string;
  created_at: string;
  items: LineaDto[];
}

export interface TurnoDto {
  id: string;
  opened_by: string;
  opened_at: string;
  closed_at: string | null;
  opening_cash: string;
  closing_cash: string | null;
  status: string;
  notes: string | null;
}

export interface CobroDto {
  id: string;
  method: string;
  amount: string;
  reference: string | null;
  processed_at: string;
}

export interface EstadoDeCobroDto {
  order_id: string;
  total: string;
  paid: string;
  due: string;
  is_settled: boolean;
  payments: CobroDto[];
}

export interface ArqueoDto {
  shift: TurnoDto;
  by_method: Record<string, string>;
  total_sold: string;
  cash_sold: string;
  expected_cash: string;
  counted_cash: string | null;
  difference: string | null;
  payments_count: number;
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

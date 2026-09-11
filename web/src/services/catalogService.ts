import { deLaApi } from '@/lib/money';
import { apiFetchServidor } from '@/services/http.server';
import type { CategoriaDto, PaginaDto, ProductoDto } from '@/types/api';
import { aPagina } from '@/services/http';
import type { Pagina } from '@/types/api';

export interface Categoria {
  id: string;
  nombre: string;
  orden: number;
  activa: boolean;
}

export interface Producto {
  id: string;
  nombre: string;
  descripcion: string | null;
  /** Centavos. El precio del negocio. */
  precioBase: number;
  /** Centavos. El que se cobra EN ESTA SUCURSAL. */
  precio: number;
  estacion: string;
  categoriaId: string | null;
  activo: boolean;
  disponible: boolean;
}

/**
 * DTO -> dominio, campo a campo.
 *
 * Es donde `"12.50"` se vuelve `1250` centavos. Un conversor generico de
 * mayusculas dejaria pasar la cadena y el fallo apareceria tres capas mas
 * arriba, al multiplicar por una cantidad.
 */
const aCategoria = (dto: CategoriaDto): Categoria => ({
  id: dto.id,
  nombre: dto.name,
  orden: dto.sort_order,
  activa: dto.is_active,
});

const aProducto = (dto: ProductoDto): Producto => ({
  id: dto.id,
  nombre: dto.name,
  descripcion: dto.description,
  precioBase: deLaApi(dto.price),
  precio: deLaApi(dto.effective_price),
  estacion: dto.station,
  categoriaId: dto.category_id,
  activo: dto.is_active,
  disponible: dto.is_available,
});

export async function listarCategorias(): Promise<Categoria[]> {
  const dtos = await apiFetchServidor<CategoriaDto[]>('/catalog/categories');
  return dtos.map(aCategoria);
}

export interface FiltroDeCarta {
  q?: string;
  categoria?: string;
  page?: number;
}

export async function listarProductos(filtro: FiltroDeCarta = {}): Promise<Pagina<Producto>> {
  const parametros = new URLSearchParams();
  if (filtro.q) parametros.set('q', filtro.q);
  if (filtro.categoria) parametros.set('categoria', filtro.categoria);
  if (filtro.page) parametros.set('page', String(filtro.page));

  const consulta = parametros.toString();
  const dto = await apiFetchServidor<PaginaDto<ProductoDto>>(
    `/catalog/products${consulta ? `?${consulta}` : ''}`,
  );
  return aPagina(dto, aProducto);
}

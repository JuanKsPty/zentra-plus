import 'server-only';

import { apiFetchServidor } from '@/services/http.server';
import { aComanda, type Comanda } from '@/services/ordersService';
import type { ComandaDto, PaginaDto } from '@/types/api';

/** Las lecturas, desde componentes de servidor. Ver `http.server.ts`. */

export async function listarAbiertas(mesaId?: string): Promise<Comanda[]> {
  const parametros = new URLSearchParams({ abiertas: 'true', size: '100' });
  if (mesaId) parametros.set('mesa', mesaId);
  const dto = await apiFetchServidor<PaginaDto<ComandaDto>>(`/orders?${parametros}`);
  return dto.items.map(aComanda);
}

export async function verComanda(ordenId: string): Promise<Comanda> {
  return aComanda(await apiFetchServidor<ComandaDto>(`/orders/${ordenId}`));
}

export async function tablero(estacion?: string): Promise<Comanda[]> {
  const consulta = estacion ? `?estacion=${encodeURIComponent(estacion)}` : '';
  const dtos = await apiFetchServidor<ComandaDto[]>(`/orders/kds${consulta}`);
  return dtos.map(aComanda);
}

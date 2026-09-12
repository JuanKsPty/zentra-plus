import { deLaApi } from '@/lib/money';
import { apiFetch } from '@/services/http';
import type { ComandaDto, LineaDto, PaginaDto } from '@/types/api';

export interface Linea {
  id: string;
  productoId: string;
  producto: string;
  precioUnitario: number;
  estacion: string;
  cantidad: number;
  subtotal: number;
  notas: string | null;
  estado: string;
}

export interface Comanda {
  id: string;
  numero: number;
  etiqueta: string | null;
  mesaId: string | null;
  mesaNumero: number | null;
  estado: string;
  subtotal: number;
  propina: number;
  total: number;
  /** La hora del HECHO, que no siempre es la de llegada. */
  ocurrioEn: Date;
  lineas: Linea[];
}

const aLinea = (dto: LineaDto): Linea => ({
  id: dto.id,
  productoId: dto.product_id,
  producto: dto.product_name,
  precioUnitario: deLaApi(dto.unit_price),
  estacion: dto.station,
  cantidad: dto.quantity,
  subtotal: deLaApi(dto.subtotal),
  notas: dto.notes,
  estado: dto.status,
});

export const aComanda = (dto: ComandaDto): Comanda => ({
  id: dto.id,
  numero: dto.order_number,
  etiqueta: dto.label,
  mesaId: dto.table_id,
  mesaNumero: dto.table_number,
  estado: dto.status,
  subtotal: deLaApi(dto.subtotal),
  propina: deLaApi(dto.tip_amount),
  total: deLaApi(dto.total),
  ocurrioEn: new Date(dto.occurred_at),
  lineas: dto.items.map(aLinea),
});

export interface LineaNueva {
  productoId: string;
  cantidad?: number;
  notas?: string;
}

export async function tomarComanda(datos: {
  mesaId?: string | null;
  etiqueta?: string;
  lineas: LineaNueva[];
}): Promise<Comanda> {
  const dto = await apiFetch<ComandaDto>('/orders', {
    method: 'POST',
    body: {
      // El identificador lo acuna el DISPOSITIVO, no el servidor. Reenviar con
      // el mismo no duplica, y es lo que hara posible la cola sin conexion sin
      // reescribir nada de esto.
      id: crypto.randomUUID(),
      table_id: datos.mesaId ?? null,
      label: datos.etiqueta,
      items: datos.lineas.map((l) => ({
        id: crypto.randomUUID(),
        product_id: l.productoId,
        quantity: l.cantidad ?? 1,
        notes: l.notas,
      })),
      // La hora del dispositivo. Si la comanda se escribio antes de que volviera
      // la red, la cocina tiene que verla en su sitio de la cola, no al final.
      occurred_at: new Date().toISOString(),
    },
  });
  return aComanda(dto);
}

export async function moverEstado(ordenId: string, estado: string): Promise<Comanda> {
  return aComanda(
    await apiFetch<ComandaDto>(`/orders/${ordenId}/status`, {
      method: 'PATCH',
      body: { status: estado, occurred_at: new Date().toISOString() },
    }),
  );
}

export async function avanzarDesdeCocina(ordenId: string, estado: string): Promise<Comanda> {
  return aComanda(
    await apiFetch<ComandaDto>(`/orders/${ordenId}/bump`, {
      method: 'PATCH',
      body: { status: estado, occurred_at: new Date().toISOString() },
    }),
  );
}

export type { PaginaDto };

import { deLaApi, paraLaApi } from '@/lib/money';
import { apiFetch } from '@/services/http';
import type { ArqueoDto, CobroDto, EstadoDeCobroDto, TurnoDto } from '@/types/api';

export interface Turno {
  id: string;
  abiertoEn: Date;
  cerradoEn: Date | null;
  fondo: number;
  contado: number | null;
  estado: string;
}

export interface Cobro {
  id: string;
  metodo: string;
  importe: number;
  referencia: string | null;
  cobradoEn: Date;
}

export interface EstadoDeCobro {
  ordenId: string;
  total: number;
  pagado: number;
  falta: number;
  saldada: boolean;
  cobros: Cobro[];
}

export interface Arqueo {
  turno: Turno;
  porMetodo: Record<string, number>;
  totalVendido: number;
  efectivoVendido: number;
  efectivoEsperado: number;
  efectivoContado: number | null;
  diferencia: number | null;
  cuantosCobros: number;
}

export const aTurno = (dto: TurnoDto): Turno => ({
  id: dto.id,
  abiertoEn: new Date(dto.opened_at),
  cerradoEn: dto.closed_at ? new Date(dto.closed_at) : null,
  fondo: deLaApi(dto.opening_cash),
  contado: dto.closing_cash === null ? null : deLaApi(dto.closing_cash),
  estado: dto.status,
});

const aCobro = (dto: CobroDto): Cobro => ({
  id: dto.id,
  metodo: dto.method,
  importe: deLaApi(dto.amount),
  referencia: dto.reference,
  cobradoEn: new Date(dto.processed_at),
});

export const aEstadoDeCobro = (dto: EstadoDeCobroDto): EstadoDeCobro => ({
  ordenId: dto.order_id,
  total: deLaApi(dto.total),
  pagado: deLaApi(dto.paid),
  falta: deLaApi(dto.due),
  saldada: dto.is_settled,
  cobros: dto.payments.map(aCobro),
});

export const aArqueo = (dto: ArqueoDto): Arqueo => ({
  turno: aTurno(dto.shift),
  porMetodo: Object.fromEntries(
    Object.entries(dto.by_method).map(([metodo, importe]) => [metodo, deLaApi(importe)]),
  ),
  totalVendido: deLaApi(dto.total_sold),
  efectivoVendido: deLaApi(dto.cash_sold),
  efectivoEsperado: deLaApi(dto.expected_cash),
  efectivoContado: dto.counted_cash === null ? null : deLaApi(dto.counted_cash),
  // `null` mientras el turno sigue abierto: «no se ha contado» NO es «cuadra».
  diferencia: dto.difference === null ? null : deLaApi(dto.difference),
  cuantosCobros: dto.payments_count,
});

export async function abrirTurno(fondoEnCentavos: number): Promise<Turno> {
  return aTurno(
    await apiFetch<TurnoDto>('/shifts/open', {
      method: 'POST',
      body: { opening_cash: paraLaApi(fondoEnCentavos) },
    }),
  );
}

export async function cerrarTurno(turnoId: string, contadoEnCentavos: number): Promise<Arqueo> {
  return aArqueo(
    await apiFetch<ArqueoDto>(`/shifts/${turnoId}/close`, {
      method: 'POST',
      body: { closing_cash: paraLaApi(contadoEnCentavos) },
    }),
  );
}

export async function cobrar(
  ordenId: string,
  metodo: string,
  importeEnCentavos: number,
): Promise<EstadoDeCobro> {
  return aEstadoDeCobro(
    await apiFetch<EstadoDeCobroDto>(`/orders/${ordenId}/payments`, {
      method: 'POST',
      body: {
        method: metodo,
        amount: paraLaApi(importeEnCentavos),
        // Clave de reenvio: si la red falla y el cajero reintenta, no se cobra
        // dos veces. Es la diferencia entre un susto y un descuadre.
        client_request_id: crypto.randomUUID(),
        occurred_at: new Date().toISOString(),
      },
    }),
  );
}

export async function ponerPropina(
  ordenId: string,
  propinaEnCentavos: number,
): Promise<EstadoDeCobro> {
  return aEstadoDeCobro(
    await apiFetch<EstadoDeCobroDto>(`/orders/${ordenId}/tip`, {
      method: 'PATCH',
      body: { tip_amount: paraLaApi(propinaEnCentavos) },
    }),
  );
}

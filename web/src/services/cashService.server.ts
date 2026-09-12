import 'server-only';

import { apiFetchServidor } from '@/services/http.server';
import { aArqueo, aEstadoDeCobro, aTurno, type Arqueo, type EstadoDeCobro, type Turno } from '@/services/cashService';
import type { ArqueoDto, EstadoDeCobroDto, TurnoDto } from '@/types/api';

/** `null` cuando no hay caja abierta: es el primer estado del dia, no un error. */
export async function turnoActual(): Promise<Turno | null> {
  const dto = await apiFetchServidor<TurnoDto | null>('/shifts/current');
  return dto ? aTurno(dto) : null;
}

export async function estadoDeCobro(ordenId: string): Promise<EstadoDeCobro> {
  return aEstadoDeCobro(await apiFetchServidor<EstadoDeCobroDto>(`/orders/${ordenId}/payments`));
}

export async function arqueoDe(turnoId: string): Promise<Arqueo> {
  return aArqueo(await apiFetchServidor<ArqueoDto>(`/shifts/${turnoId}/summary`));
}

export async function metodosDeCobro(): Promise<Record<string, string>> {
  return apiFetchServidor<Record<string, string>>('/payment-methods');
}

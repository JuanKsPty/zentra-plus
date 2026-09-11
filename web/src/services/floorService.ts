import { apiFetchServidor } from '@/services/http.server';
import type { MesaDto, SectorDto } from '@/types/api';

export interface Zona {
  id: string;
  nombre: string;
  orden: number;
  activa: boolean;
}

export interface Mesa {
  id: string;
  numero: number;
  capacidad: number;
  forma: string;
  x: number | null;
  y: number | null;
  zonaId: string;
  estado: string;
}

const aZona = (dto: SectorDto): Zona => ({
  id: dto.id,
  nombre: dto.name,
  orden: dto.sort_order,
  activa: dto.is_active,
});

const aMesa = (dto: MesaDto): Mesa => ({
  id: dto.id,
  numero: dto.number,
  capacidad: dto.capacity,
  forma: dto.shape,
  x: dto.position_x,
  y: dto.position_y,
  zonaId: dto.sector_id,
  estado: dto.status,
});

export async function listarZonas(): Promise<Zona[]> {
  return (await apiFetchServidor<SectorDto[]>('/floor/sectors')).map(aZona);
}

export async function listarMesas(): Promise<Mesa[]> {
  return (await apiFetchServidor<MesaDto[]>('/floor/tables')).map(aMesa);
}

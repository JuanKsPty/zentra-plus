import { apiFetch } from '@/services/http';
import type { UsuarioOperativoDto } from '@/types/api';

export interface UsuarioOperativo {
  id: string;
  name: string;
  roleName: string | null;
}

const aOperativo = (dto: UsuarioOperativoDto): UsuarioOperativo => ({
  id: dto.id,
  name: dto.name,
  roleName: dto.role_name,
});

/** La rejilla del teclado de PIN. Publica: hay que verla antes de tener sesion. */
export async function listarOperativos(): Promise<UsuarioOperativo[]> {
  const dtos = await apiFetch<UsuarioOperativoDto[]>('/users/operational');
  return dtos.map(aOperativo);
}

import { apiFetch } from '@/services/http';
import type { Salud, SaludDto } from '@/types/api';

/**
 * DTO -> dominio, campo a campo.
 *
 * Parece de sobra con una forma tan simple, y es la plantilla del resto: es
 * donde snake_case pasa a camelCase y donde una cadena ISO se vuelve Date.
 * Un conversor generico dejaria pasar las cadenas y el fallo apareceria tres
 * capas mas arriba, al operar con ellas.
 */
const aSalud = (dto: SaludDto): Salud => ({
  status: dto.status,
  app: dto.app,
  version: dto.version,
  environment: dto.environment,
});

export async function obtenerSalud(): Promise<Salud> {
  return aSalud(await apiFetch<SaludDto>('/health'));
}

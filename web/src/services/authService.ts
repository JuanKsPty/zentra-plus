import { apiFetch, recordarPuerta } from '@/services/http';
import type { UsuarioDto } from '@/types/api';

export interface Usuario {
  id: string;
  name: string;
  email: string | null;
  roleName: string | null;
}

const aUsuario = (dto: UsuarioDto): Usuario => ({
  id: dto.id,
  name: dto.name,
  email: dto.email,
  roleName: dto.role_name ?? null,
});

export async function entrarConCorreo(email: string, password: string): Promise<Usuario> {
  const usuario = aUsuario(
    await apiFetch<UsuarioDto>('/auth/login', { method: 'POST', body: { email, password } }),
  );
  recordarPuerta('email');
  return usuario;
}

export async function entrarConPin(userId: string, pin: string): Promise<Usuario> {
  const usuario = aUsuario(
    await apiFetch<UsuarioDto>('/auth/pin', { method: 'POST', body: { user_id: userId, pin } }),
  );
  recordarPuerta('pin');
  return usuario;
}

export async function cerrarSesion(): Promise<void> {
  await apiFetch<void>('/auth/logout', { method: 'POST' });
}

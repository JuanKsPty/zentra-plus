import { redirect } from 'next/navigation';

import { destinoPara } from '@/lib/auth/landing';
import { obtenerSesion } from '@/lib/auth/session';

/**
 * La puerta. No pinta nada: decide a donde va cada persona.
 *
 * Es tambien el punto de entrada del icono instalado: el `start_url` se congela
 * cuando alguien anade la aplicacion a su pantalla de inicio, asi que no puede
 * saber quien la abrira. Aqui si.
 */
export default async function Inicio() {
  const sesion = await obtenerSesion();
  redirect(sesion ? destinoPara(sesion.permissions) : '/acceso');
}

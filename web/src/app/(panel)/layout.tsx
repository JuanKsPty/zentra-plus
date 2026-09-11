import { redirect } from 'next/navigation';

import { BarraInferior } from '@/components/shell/bottom-nav';
import { BarraLateral } from '@/components/shell/app-sidebar';
import { CabeceraDeApp } from '@/components/shell/app-header';
import { obtenerSesion } from '@/lib/auth/session';

export default async function LayoutDelPanel({ children }: { children: React.ReactNode }) {
  const sesion = await obtenerSesion();
  // Defensa en profundidad: el middleware ya bloquea el prefijo, pero un layout
  // que confia en el middleware deja de proteger el dia que alguien toca el
  // matcher. Y la autorizacion de verdad la hace la API; esto solo evita pintar
  // una pantalla que va a dar 403.
  if (!sesion) redirect('/acceso');

  return (
    <div className="flex min-h-dvh">
      <BarraLateral permisos={sesion.permissions} />
      <div className="flex min-w-0 flex-1 flex-col">
        <CabeceraDeApp sesion={sesion} />
        {/* pb-20 en movil: sin el, la barra del pulgar tapa el ultimo elemento
            de cualquier lista y parece que la lista termina antes. */}
        <main className="flex-1 p-4 pb-20 md:p-6 sm:pb-6">{children}</main>
        <BarraInferior permisos={sesion.permissions} />
      </div>
    </div>
  );
}

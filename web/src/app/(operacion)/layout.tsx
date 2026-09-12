import Link from 'next/link';
import { redirect } from 'next/navigation';

import { Button } from '@/components/ui/button';
import { InterruptorDeTema } from '@/components/shell/theme-toggle';
import { MenuDeUsuario } from '@/components/shell/user-menu';
import { obtenerSesion } from '@/lib/auth/session';
import { destinoPara } from '@/lib/auth/landing';

/**
 * La cascara de las pantallas OPERATIVAS: salon, comanda y cocina.
 *
 * Sin barra lateral y sin menus: se usan de pie, con las manos ocupadas y con
 * prisa. Todo lo que se pulsa aqui mide 44 px como minimo, a cualquier ancho.
 */
export default async function LayoutDeOperacion({ children }: { children: React.ReactNode }) {
  const sesion = await obtenerSesion();
  if (!sesion) redirect('/acceso');

  const puedeSalon = sesion.permissions.includes('orders:write');
  const puedeCocina = sesion.permissions.includes('orders:bump');
  const puedeCaja = sesion.permissions.includes('cash:read');

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-3">
        <span className="font-heading text-base font-semibold tracking-tight">Zentra+</span>

        <nav className="ml-2 flex gap-1">
          {puedeSalon && <Salto href="/salon" texto="Salon" />}
          {puedeCocina && <Salto href="/cocina" texto="Cocina" />}
          {puedeCaja && <Salto href="/caja" texto="Caja" />}
        </nav>

        <div className="flex-1" />
        <InterruptorDeTema />
        <MenuDeUsuario sesion={sesion} />
      </header>

      <main className="flex-1 p-3 sm:p-4">{children}</main>

      {/* Si alguien llega aqui sin ninguna superficie operativa, se le manda a
          la suya en vez de dejarlo en una pantalla vacia. */}
      {!puedeSalon && !puedeCocina && !puedeCaja && redirect(destinoPara(sesion.permissions))}
    </div>
  );
}

function Salto({ href, texto }: { href: string; texto: string }) {
  return (
    <Button variant="ghost" size="touch" nativeButton={false} render={<Link href={href} />}>
      {texto}
    </Button>
  );
}

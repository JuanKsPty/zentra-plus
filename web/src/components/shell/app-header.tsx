import { HuecoDeSucursal } from '@/components/shell/branch-slot';
import { MenuDeUsuario } from '@/components/shell/user-menu';
import { InterruptorDeTema } from '@/components/shell/theme-toggle';
import type { Sesion } from '@/lib/auth/session';

export function CabeceraDeApp({ sesion }: { sesion: Sesion }) {
  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4 md:px-6">
      <span className="font-heading text-base font-semibold tracking-tight sm:hidden">
        Zentra+
      </span>
      <div className="flex-1" />
      <HuecoDeSucursal sesion={sesion} />
      <InterruptorDeTema />
      <MenuDeUsuario sesion={sesion} />
    </header>
  );
}

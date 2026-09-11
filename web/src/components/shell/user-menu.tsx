'use client';

import { LogOutIcon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { Sesion } from '@/lib/auth/session';
import { cerrarSesion } from '@/services/authService';

const iniciales = (nombre: string) =>
  nombre
    .split(/\s+/)
    .slice(0, 2)
    .map((parte) => parte[0] ?? '')
    .join('')
    .toUpperCase();

export function MenuDeUsuario({ sesion }: { sesion: Sesion }) {
  const router = useRouter();
  const [saliendo, setSaliendo] = useState(false);

  async function salir() {
    setSaliendo(true);
    await cerrarSesion();
    // `refresh()` ademas de `push`: sin el, el arbol de componentes de servidor
    // se queda en cache con la sesion vieja y al volver atras se ve el panel de
    // quien acaba de salir.
    router.push('/acceso');
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon-sm" aria-label="Tu cuenta">
            <Avatar className="size-7">
              <AvatarFallback>{iniciales(sesion.name)}</AvatarFallback>
            </Avatar>
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel>
          <span className="block truncate font-medium">{sesion.name}</span>
          <span className="block truncate text-xs font-normal text-muted-foreground">
            {sesion.roleName ?? 'Sin puesto'}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={salir} disabled={saliendo}>
          <LogOutIcon />
          {saliendo ? 'Saliendo...' : 'Cerrar sesion'}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

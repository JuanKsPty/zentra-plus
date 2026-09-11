'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import {
  DESTINOS,
  ETIQUETAS_DE_GRUPO,
  destinosPara,
  esDestinoActivo,
  type Destino,
} from '@/config/navigation';
import { cn } from '@/lib/utils';

export function BarraLateral({ permisos }: { permisos: readonly string[] }) {
  const ruta = usePathname();
  const visibles = destinosPara(permisos);

  const porGrupo = (['operacion', 'negocio', 'configuracion'] as const)
    .map((grupo) => [grupo, visibles.filter((d) => d.grupo === grupo)] as const)
    .filter(([, destinos]) => destinos.length > 0);

  return (
    // Oculta por debajo de 640 px: ahi manda la barra inferior del pulgar.
    <nav className="hidden w-56 shrink-0 border-r border-border bg-card sm:block">
      <div className="flex h-14 items-center px-4">
        <span className="font-heading text-base font-semibold tracking-tight">Zentra+</span>
      </div>

      <div className="space-y-6 px-3 py-2">
        {porGrupo.map(([grupo, destinos]) => (
          <div key={grupo} className="space-y-1">
            <p className="px-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {ETIQUETAS_DE_GRUPO[grupo]}
            </p>
            {destinos.map((destino) => (
              <EnlaceDeNavegacion key={destino.id} destino={destino} ruta={ruta} />
            ))}
          </div>
        ))}
      </div>

      {visibles.length === 0 && (
        <p className="px-5 text-xs text-muted-foreground">
          Tu usuario todavia no tiene ningun modulo asignado.
        </p>
      )}

      {DESTINOS.length === 0 && null}
    </nav>
  );
}

function EnlaceDeNavegacion({ destino, ruta }: { destino: Destino; ruta: string }) {
  const activo = esDestinoActivo(destino.href, ruta);
  const Icono = destino.icono;

  return (
    <Link
      href={destino.href}
      aria-current={activo ? 'page' : undefined}
      className={cn(
        'flex h-9 items-center gap-2.5 rounded-lg px-2 text-sm transition-colors',
        activo
          ? 'bg-accent font-medium text-accent-foreground'
          : 'text-muted-foreground hover:bg-muted hover:text-foreground',
      )}
    >
      <Icono className="size-4 shrink-0" />
      {destino.etiqueta}
    </Link>
  );
}

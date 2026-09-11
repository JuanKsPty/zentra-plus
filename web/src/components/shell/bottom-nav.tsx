'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

import { destinosDeBarraPara, esDestinoActivo } from '@/config/navigation';
import { cn } from '@/lib/utils';

/**
 * La barra del pulgar. Solo por debajo de 640 px.
 *
 * Cuatro destinos, que es lo que cabe sin que los objetivos bajen del suelo
 * tactil. El cajon lateral se abre desde la esquina superior izquierda, que es
 * exactamente donde no llega quien sujeta un telefono con una mano — por eso lo
 * que se usa a diario esta aqui abajo y no ahi arriba.
 */
export function BarraInferior({ permisos }: { permisos: readonly string[] }) {
  const ruta = usePathname();
  const destinos = destinosDeBarraPara(permisos);

  if (destinos.length === 0) return null;

  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 border-t border-border bg-card sm:hidden">
      <ul className="flex">
        {destinos.map((destino) => {
          const activo = esDestinoActivo(destino.href, ruta);
          const Icono = destino.icono;
          return (
            <li key={destino.id} className="flex-1">
              <Link
                href={destino.href}
                aria-current={activo ? 'page' : undefined}
                className={cn(
                  // h-14 sin prefijo: esta barra solo existe en movil, asi que
                  // no hay un valor de escritorio que pisar.
                  'flex h-14 flex-col items-center justify-center gap-0.5 text-xs',
                  activo ? 'text-primary' : 'text-muted-foreground',
                )}
              >
                <Icono className="size-5" />
                {destino.etiqueta}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

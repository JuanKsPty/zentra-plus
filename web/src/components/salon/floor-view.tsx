import Link from 'next/link';

import { Dinero } from '@/components/shared/money';
import { cn } from '@/lib/utils';
import type { Comanda } from '@/services/ordersService';
import type { Mesa, Zona } from '@/services/floorService';

const ESTADOS: Record<string, string> = {
  available: 'border-border bg-card',
  occupied: 'border-info/30 bg-info/12',
  cleaning: 'border-warning/30 bg-warning/12',
  reserved: 'border-info/30 bg-info/12',
  maintenance: 'border-destructive/30 bg-destructive/12 opacity-60',
};

const ETIQUETAS: Record<string, string> = {
  available: 'Libre',
  occupied: 'Ocupada',
  cleaning: 'Por recoger',
  reserved: 'Reservada',
  maintenance: 'Fuera de servicio',
};

export function SalonEnVivo({
  zonas,
  mesas,
  comandas,
}: {
  zonas: Zona[];
  mesas: Mesa[];
  comandas: Comanda[];
}) {
  const porMesa = new Map<string, Comanda[]>();
  for (const comanda of comandas) {
    if (!comanda.mesaId) continue;
    porMesa.set(comanda.mesaId, [...(porMesa.get(comanda.mesaId) ?? []), comanda]);
  }

  return (
    <div className="space-y-8">
      {zonas.map((zona) => {
        const suyas = mesas.filter((mesa) => mesa.zonaId === zona.id);
        if (suyas.length === 0) return null;

        return (
          <section key={zona.id} className="space-y-3">
            <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {zona.nombre}
            </h2>
            <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
              {suyas.map((mesa) => (
                <MesaEnVivo key={mesa.id} mesa={mesa} comandas={porMesa.get(mesa.id) ?? []} />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function MesaEnVivo({ mesa, comandas }: { mesa: Mesa; comandas: Comanda[] }) {
  const cuenta = comandas[0];
  const total = comandas.reduce((suma, comanda) => suma + comanda.total, 0);

  // Con cuenta abierta se va a la comanda; sin ella, a tomar una nueva. Es el
  // gesto que el mesero hace mil veces al dia: un solo toque, sin menu.
  const destino = cuenta ? `/comanda/${cuenta.id}` : `/comanda/nueva?mesa=${mesa.id}`;

  return (
    <li>
      <Link
        href={destino}
        className={cn(
          // min-h-24 sin prefijo: esta pantalla se usa de pie a cualquier ancho.
          'flex min-h-24 flex-col items-center justify-center gap-1 border p-3 text-center transition-colors',
          mesa.forma === 'round' ? 'rounded-full' : 'rounded-xl',
          ESTADOS[mesa.estado] ?? ESTADOS.available,
        )}
      >
        <span className="font-mono text-2xl font-semibold tabular-nums">{mesa.numero}</span>
        {cuenta ? (
          <Dinero centavos={total} className="text-sm font-medium" />
        ) : (
          <span className="text-xs text-muted-foreground">
            {ETIQUETAS[mesa.estado] ?? mesa.estado}
          </span>
        )}
        {comandas.length > 1 && (
          <span className="text-xs text-muted-foreground">{comandas.length} cuentas</span>
        )}
      </Link>
    </li>
  );
}

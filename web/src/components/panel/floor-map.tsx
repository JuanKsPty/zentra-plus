import { cn } from '@/lib/utils';
import type { Mesa, Zona } from '@/services/floorService';

/**
 * El estado de una mesa, en color.
 *
 * `cleaning` existe y no sobra: una mesa recien cobrada NO esta libre. Si el
 * sistema dijera que lo esta, el anfitrion sienta a alguien encima de los platos
 * del anterior.
 *
 * Relleno tenue = estado. El solido se reserva para lo que se pulsa.
 */
const ESTADOS: Record<string, { etiqueta: string; clase: string }> = {
  available: { etiqueta: 'Libre', clase: 'border-border bg-card text-muted-foreground' },
  occupied: { etiqueta: 'Ocupada', clase: 'border-info/25 bg-info/12 text-info' },
  cleaning: { etiqueta: 'Por recoger', clase: 'border-warning/25 bg-warning/12 text-warning' },
  reserved: { etiqueta: 'Reservada', clase: 'border-info/25 bg-info/12 text-info' },
  maintenance: {
    etiqueta: 'Fuera de servicio',
    clase: 'border-destructive/25 bg-destructive/12 text-destructive',
  },
};

export function MapaDelSalon({ zonas, mesas }: { zonas: Zona[]; mesas: Mesa[] }) {
  const porZona = zonas.map((zona) => ({
    zona,
    mesas: mesas.filter((mesa) => mesa.zonaId === zona.id),
  }));

  return (
    <div className="space-y-8">
      {porZona.map(({ zona, mesas: suyas }) => (
        <section key={zona.id} className="space-y-3">
          <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {zona.nombre} · {suyas.length} mesas
          </h2>
          <ul className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
            {suyas.map((mesa) => {
              const estado = ESTADOS[mesa.estado] ?? ESTADOS.available!;
              return (
                <li
                  key={mesa.id}
                  className={cn(
                    // Los objetivos del salon no bajan de 44 px a ningun ancho:
                    // se tocan de pie y con las manos ocupadas.
                    'flex min-h-20 flex-col items-center justify-center gap-1 border p-3 text-center',
                    mesa.forma === 'round' ? 'rounded-full' : 'rounded-xl',
                    estado.clase,
                  )}
                >
                  <span className="font-mono text-lg font-semibold tabular-nums">
                    {mesa.numero}
                  </span>
                  <span className="text-xs">{estado.etiqueta}</span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';

import { cn } from '@/lib/utils';

/**
 * Cuanto lleva esperando una comanda.
 *
 * Cuenta EN LOCAL con un temporizador. Refrescar la pantalla cada segundo para
 * mover un contador seria la peticion mas cara y mas inutil del sistema, y con
 * seis fichas en cola serian seis por segundo.
 *
 * Se cuenta desde la hora del HECHO, no desde la de llegada: una comanda que
 * espero diez minutos a que volviera la red lleva diez minutos esperando, y el
 * tablero tiene que decirlo.
 */
export function Transcurrido({ desde }: { desde: Date }) {
  const [minutos, setMinutos] = useState(() => transcurridos(desde));

  useEffect(() => {
    const cada = setInterval(() => setMinutos(transcurridos(desde)), 30_000);
    // Al volver a la pestana se recalcula: un temporizador en segundo plano se
    // ralentiza y el contador se queda corto.
    const alVolver = () => setMinutos(transcurridos(desde));
    document.addEventListener('visibilitychange', alVolver);
    return () => {
      clearInterval(cada);
      document.removeEventListener('visibilitychange', alVolver);
    };
  }, [desde]);

  return (
    <span
      className={cn(
        'font-mono text-sm tabular-nums',
        minutos >= 15 ? 'text-destructive' : minutos >= 8 ? 'text-warning' : 'text-muted-foreground',
      )}
    >
      {minutos} min
    </span>
  );
}

function transcurridos(desde: Date): number {
  return Math.max(0, Math.floor((Date.now() - desde.getTime()) / 60_000));
}

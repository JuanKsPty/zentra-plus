'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dinero } from '@/components/shared/money';
import { reportar } from '@/lib/errores';
import { moverEstado, type Comanda } from '@/services/ordersService';

const ETIQUETAS: Record<string, string> = {
  pending: 'Pendiente',
  preparing: 'En preparacion',
  ready: 'Lista',
  delivered: 'Entregada',
  closed: 'Cobrada',
  cancelled: 'Anulada',
};

const COLORES: Record<string, string> = {
  pending: 'border-info/25 bg-info/12 text-info',
  preparing: 'border-warning/25 bg-warning/12 text-warning',
  ready: 'border-success/25 bg-success/12 text-success',
  delivered: 'border-success/25 bg-success/12 text-success',
  closed: 'border-muted-foreground/25 bg-muted text-muted-foreground',
  cancelled: 'border-destructive/25 bg-destructive/12 text-destructive',
};

/**
 * Que se puede hacer desde cada estado, en el orden en que el salon lo hace.
 *
 * NO hay boton de «cobrada»: una cuenta se cierra COBRANDOLA, en caja. Pintar
 * ese boton aqui es el agujero de dinero mas facil de abrir — un toque y la
 * cuenta sale de «por cobrar» con la mesa liberada.
 */
const SIGUIENTES: Record<string, { estado: string; texto: string }[]> = {
  pending: [{ estado: 'cancelled', texto: 'Anular' }],
  preparing: [{ estado: 'cancelled', texto: 'Anular' }],
  ready: [{ estado: 'delivered', texto: 'Entregada' }],
  delivered: [],
  closed: [],
  cancelled: [],
};

export function DetalleDeComanda({ comanda }: { comanda: Comanda }) {
  const router = useRouter();
  const [enviando, setEnviando] = useState<string | null>(null);

  async function mover(estado: string) {
    setEnviando(estado);
    try {
      await moverEstado(comanda.id, estado);
      router.refresh();
    } catch (error) {
      reportar(error, `La cuenta #${comanda.numero} sigue como estaba.`);
    } finally {
      setEnviando(null);
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="font-heading text-2xl font-semibold tracking-tight">
            Cuenta #<span className="font-mono tabular-nums">{comanda.numero}</span>
          </h1>
          <p className="text-sm text-muted-foreground">
            {comanda.mesaNumero ? `Mesa ${comanda.mesaNumero}` : (comanda.etiqueta ?? 'Sin mesa')}
          </p>
        </div>
        <Badge className={COLORES[comanda.estado]}>{ETIQUETAS[comanda.estado]}</Badge>
      </header>

      <ul className="divide-y divide-border rounded-xl border border-border bg-card">
        {comanda.lineas.map((linea) => (
          <li key={linea.id} className="flex items-baseline gap-3 p-4">
            <span className="font-mono tabular-nums text-muted-foreground">
              {linea.cantidad}&times;
            </span>
            <span className="min-w-0 flex-1">
              {linea.producto}
              {linea.notas && <span className="block text-xs text-warning">{linea.notas}</span>}
            </span>
            <Dinero centavos={linea.subtotal} />
          </li>
        ))}
      </ul>

      <div className="flex items-baseline justify-between rounded-xl border border-border bg-card px-4 py-3">
        <span className="text-sm text-muted-foreground">Total</span>
        <Dinero centavos={comanda.total} className="text-2xl font-semibold" />
      </div>

      <div className="flex flex-wrap gap-3">
        {SIGUIENTES[comanda.estado]?.map((paso) => (
          <Button
            key={paso.estado}
            size="key"
            variant={paso.estado === 'cancelled' ? 'destructive' : 'default'}
            disabled={enviando !== null}
            onClick={() => mover(paso.estado)}
          >
            {enviando === paso.estado ? 'Guardando...' : paso.texto}
          </Button>
        ))}
      </div>

      {comanda.estado === 'delivered' && (
        <p className="text-sm text-muted-foreground">
          Entregada. Se cierra al cobrarla, en caja.
        </p>
      )}
    </div>
  );
}

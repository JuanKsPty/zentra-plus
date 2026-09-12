import Link from 'next/link';

import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { Refrescador } from '@/components/realtime/realtime-refresher';
import { SinNada } from '@/components/shared/empty-state';
import { Button } from '@/components/ui/button';
import { Dinero } from '@/components/shared/money';
import { turnoActual } from '@/services/cashService.server';
import { listarAbiertas } from '@/services/ordersService.server';

export const metadata = { title: 'Caja · Zentra+' };

export default async function Caja() {
  let datos;
  try {
    const [turno, cuentas] = await Promise.all([turnoActual(), listarAbiertas()]);
    datos = { turno, cuentas };
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  const { turno, cuentas } = datos;
  const porCobrar = cuentas.filter((c) => c.estado === 'delivered' || c.estado === 'ready');

  return (
    <div className="space-y-5">
      <Refrescador eventos={['order.changed', 'order.created', 'shift.changed']} />

      {/* El estado de la caja va ARRIBA del todo: sin turno abierto no se puede
          cobrar, y descubrirlo despues de armar el cobro es perder el tiempo
          justo cuando hay cola. */}
      {turno ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-success/25 bg-success/12 px-4 py-3">
          <span className="text-sm text-success">
            Caja abierta desde las{' '}
            {turno.abiertoEn.toLocaleTimeString('es-PA', {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          <Button variant="outline" size="touch" nativeButton={false} render={<Link href="/caja/turno" />}>
            Cerrar caja
          </Button>
        </div>
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-warning/25 bg-warning/12 px-4 py-3">
          <span className="text-sm text-warning">
            No tienes caja abierta. Sin caja no se puede cobrar.
          </span>
          <Button size="touch" nativeButton={false} render={<Link href="/caja/turno" />}>
            Abrir caja
          </Button>
        </div>
      )}

      <h1 className="font-heading text-xl font-semibold tracking-tight">Cuentas por cobrar</h1>

      {porCobrar.length === 0 ? (
        <SinNada
          titulo="Nada por cobrar"
          descripcion="Las cuentas aparecen aqui cuando el salon las marca como entregadas."
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {porCobrar.map((cuenta) => (
            <li key={cuenta.id}>
              <Link
                href={`/caja/cuenta/${cuenta.id}`}
                className="flex min-h-24 flex-col justify-between rounded-xl border border-border bg-card p-4 transition-colors hover:bg-accent"
              >
                <div className="flex items-baseline justify-between gap-2">
                  <span className="font-mono text-lg font-semibold tabular-nums">
                    #{cuenta.numero}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {cuenta.mesaNumero ? `Mesa ${cuenta.mesaNumero}` : (cuenta.etiqueta ?? '')}
                  </span>
                </div>
                <Dinero centavos={cuenta.total} className="text-xl font-semibold" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

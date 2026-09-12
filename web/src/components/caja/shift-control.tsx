'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Dinero } from '@/components/shared/money';
import { Field, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { deLaApi } from '@/lib/money';
import { reportar } from '@/lib/errores';
import { abrirTurno, cerrarTurno, type Arqueo, type Turno } from '@/services/cashService';

const ETIQUETAS: Record<string, string> = {
  cash: 'Efectivo',
  card: 'Tarjeta',
  transfer: 'Transferencia',
  wallet: 'Billetera',
};

export function ControlDeCaja({ turno, arqueo }: { turno: Turno | null; arqueo: Arqueo | null }) {
  const router = useRouter();
  const [importe, setImporte] = useState('');
  const [enviando, setEnviando] = useState(false);

  async function enviar() {
    const centavos = deLaApi(importe.replace(',', '.') || '0');
    setEnviando(true);
    try {
      if (turno) {
        const cierre = await cerrarTurno(turno.id, centavos);
        const diferencia = cierre.diferencia ?? 0;
        if (diferencia === 0) toast.success('Caja cerrada. Cuadra exacto.');
        else
          toast.warning(
            `Caja cerrada con una diferencia de ${(diferencia / 100).toFixed(2)}.`,
          );
      } else {
        await abrirTurno(centavos);
        toast.success('Caja abierta.');
      }
      router.push('/caja');
      router.refresh();
    } catch (error) {
      setEnviando(false);
      reportar(error, turno ? 'La caja NO se cerro.' : 'La caja NO se abrio.');
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-5">
      <h1 className="font-heading text-xl font-semibold tracking-tight">
        {turno ? 'Cerrar caja' : 'Abrir caja'}
      </h1>

      {arqueo && (
        <section className="space-y-3 rounded-xl border border-border bg-card p-4">
          <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Lo que lleva este turno
          </h2>
          <dl className="space-y-1.5 text-sm">
            {/* Todos los metodos, aunque valgan cero: un desglose con huecos
                obliga al cajero a recordar cuales faltan. */}
            {Object.entries(arqueo.porMetodo).map(([metodo, cobrado]) => (
              <div key={metodo} className="flex justify-between">
                <dt className="text-muted-foreground">{ETIQUETAS[metodo] ?? metodo}</dt>
                <Dinero centavos={cobrado} />
              </div>
            ))}
            <div className="flex justify-between border-t border-border pt-1.5 font-medium">
              <dt>Efectivo esperado en el cajon</dt>
              <Dinero centavos={arqueo.efectivoEsperado} />
            </div>
            <p className="text-xs text-muted-foreground">
              Fondo de apertura <Dinero centavos={arqueo.turno.fondo} /> +{' '}
              <Dinero centavos={arqueo.efectivoVendido} /> cobrados en efectivo
            </p>
          </dl>
        </section>
      )}

      <Field>
        <FieldLabel htmlFor="importe">
          {turno ? 'Efectivo contado en el cajon' : 'Fondo con el que abres'}
        </FieldLabel>
        <Input
          id="importe"
          inputMode="decimal"
          value={importe}
          onChange={(evento) => setImporte(evento.target.value)}
          placeholder="0.00"
          className="font-mono tabular-nums"
        />
      </Field>

      <Button size="key" className="w-full" disabled={enviando} onClick={enviar}>
        {enviando ? 'Guardando...' : turno ? 'Cerrar caja' : 'Abrir caja'}
      </Button>

      {turno && (
        <p className="text-sm text-muted-foreground">
          Cuenta el efectivo antes de escribirlo. La diferencia se calcula sola y queda
          guardada con el turno.
        </p>
      )}
    </div>
  );
}

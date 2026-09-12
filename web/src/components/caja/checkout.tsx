'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Dinero } from '@/components/shared/money';
import { Field, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { deLaApi, formatearDinero } from '@/lib/money';
import { reportar } from '@/lib/errores';
import { cn } from '@/lib/utils';
import { cobrar, type EstadoDeCobro } from '@/services/cashService';
import type { Comanda } from '@/services/ordersService';

export function PantallaDeCobro({
  comanda,
  inicial,
  metodos,
  hayTurno,
}: {
  comanda: Comanda;
  inicial: EstadoDeCobro;
  metodos: Record<string, string>;
  hayTurno: boolean;
}) {
  const router = useRouter();
  const [estado, setEstado] = useState(inicial);
  const [metodo, setMetodo] = useState('cash');
  const [recibido, setRecibido] = useState('');
  const [enviando, setEnviando] = useState(false);

  const recibidoEnCentavos = recibido ? deLaApi(recibido.replace(',', '.')) : 0;
  // Lo que se cobra: lo que falta, o lo que el cliente entrega si es menos.
  // Entregar de MAS no cobra de mas — la diferencia es cambio.
  const aCobrar = Math.min(recibidoEnCentavos || estado.falta, estado.falta);
  const cambio = Math.max(0, recibidoEnCentavos - estado.falta);

  async function registrar() {
    setEnviando(true);
    try {
      const siguiente = await cobrar(comanda.id, metodo, aCobrar);
      setEstado(siguiente);
      setRecibido('');
      if (siguiente.saldada) {
        toast.success(`Cuenta #${comanda.numero} cobrada.`);
        router.push('/caja');
      }
      router.refresh();
    } catch (error) {
      // El cobro es donde mas duele no saber si entro: el aviso dice que NO se
      // registro, para que el cajero no lo de por hecho ni lo cobre dos veces.
      reportar(error, 'El cobro NO se registro.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-5">
      <header className="flex items-baseline justify-between gap-3">
        <h1 className="font-heading text-2xl font-semibold tracking-tight">
          Cuenta #<span className="font-mono tabular-nums">{comanda.numero}</span>
        </h1>
        <span className="text-sm text-muted-foreground">
          {comanda.mesaNumero ? `Mesa ${comanda.mesaNumero}` : (comanda.etiqueta ?? '')}
        </span>
      </header>

      {!hayTurno && (
        <div className="rounded-xl border border-warning/25 bg-warning/12 px-4 py-3">
          <p className="text-sm text-warning">
            No tienes caja abierta. Sin caja no se puede cobrar.
          </p>
          <Button
            size="touch"
            className="mt-3"
            nativeButton={false}
            render={<Link href="/caja/turno" />}
          >
            Abrir caja
          </Button>
        </div>
      )}

      {/* El total grande y arriba: es la pantalla donde un error cuesta dinero,
          asi que la cifra que importa no se busca. */}
      <div className="rounded-xl border border-border bg-card p-5 text-center">
        <p className="text-xs uppercase tracking-wider text-muted-foreground">
          {estado.saldada ? 'Cobrada' : 'Falta por cobrar'}
        </p>
        <Dinero
          centavos={estado.saldada ? estado.total : estado.falta}
          className={cn('mt-1 block text-4xl font-semibold', estado.saldada && 'text-success')}
        />
        {estado.pagado > 0 && !estado.saldada && (
          <p className="mt-2 text-sm text-muted-foreground">
            Ya se cobraron <Dinero centavos={estado.pagado} /> de{' '}
            <Dinero centavos={estado.total} />
          </p>
        )}
      </div>

      {estado.cobros.length > 0 && (
        <ul className="divide-y divide-border rounded-xl border border-border bg-card text-sm">
          {estado.cobros.map((cobro) => (
            <li key={cobro.id} className="flex justify-between px-4 py-2.5">
              <span className="text-muted-foreground">{metodos[cobro.metodo] ?? cobro.metodo}</span>
              <Dinero centavos={cobro.importe} />
            </li>
          ))}
        </ul>
      )}

      {!estado.saldada && (
        <>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(metodos).map(([clave, etiqueta]) => (
              <Button
                key={clave}
                size="touch"
                variant={metodo === clave ? 'default' : 'outline'}
                onClick={() => setMetodo(clave)}
              >
                {etiqueta}
              </Button>
            ))}
          </div>

          <Field>
            <FieldLabel htmlFor="recibido">
              {metodo === 'cash' ? 'Con cuanto paga' : 'Importe'}
            </FieldLabel>
            <Input
              id="recibido"
              inputMode="decimal"
              value={recibido}
              onChange={(evento) => setRecibido(evento.target.value)}
              placeholder={formatearDinero(estado.falta).replace(/[^\d.,]/g, '')}
              className="font-mono text-lg tabular-nums"
            />
          </Field>

          {cambio > 0 && (
            <p className="rounded-lg bg-muted px-4 py-3 text-center">
              Cambio: <Dinero centavos={cambio} className="text-xl font-semibold" />
            </p>
          )}

          <Button
            size="key"
            className="w-full"
            disabled={enviando || !hayTurno || aCobrar <= 0}
            onClick={registrar}
          >
            {enviando ? 'Cobrando...' : `Cobrar ${formatearDinero(aCobrar)}`}
          </Button>

          {recibidoEnCentavos > 0 && recibidoEnCentavos < estado.falta && (
            <p className="text-center text-sm text-muted-foreground">
              Pago parcial. Quedaran <Dinero centavos={estado.falta - aCobrar} /> por cobrar.
            </p>
          )}
        </>
      )}
    </div>
  );
}

'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Transcurrido } from '@/components/cocina/elapsed';
import { reportar } from '@/lib/errores';
import { avanzarDesdeCocina, type Comanda } from '@/services/ordersService';

const COLUMNAS = [
  { estado: 'pending', titulo: 'Pendientes', siguiente: 'preparing', accion: 'Empezar' },
  { estado: 'preparing', titulo: 'En preparacion', siguiente: 'ready', accion: 'Lista' },
] as const;

export function Tablero({ comandas, estacion }: { comandas: Comanda[]; estacion?: string }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {COLUMNAS.map((columna) => {
        const suyas = comandas.filter((c) => c.estado === columna.estado);
        return (
          <section key={columna.estado} className="space-y-3">
            <h2 className="flex items-baseline gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {columna.titulo}
              <span className="font-mono tabular-nums">{suyas.length}</span>
            </h2>
            <ul className="space-y-3">
              {suyas.map((comanda) => (
                <Ficha
                  key={comanda.id}
                  comanda={comanda}
                  siguiente={columna.siguiente}
                  accion={columna.accion}
                  estacion={estacion}
                />
              ))}
            </ul>
          </section>
        );
      })}
    </div>
  );
}

function Ficha({
  comanda,
  siguiente,
  accion,
  estacion,
}: {
  comanda: Comanda;
  siguiente: string;
  accion: string;
  estacion?: string;
}) {
  const router = useRouter();
  const [enviando, setEnviando] = useState(false);

  async function avanzar() {
    setEnviando(true);
    try {
      await avanzarDesdeCocina(comanda.id, siguiente);
      router.refresh();
    } catch (error) {
      setEnviando(false);
      reportar(error, `La comanda #${comanda.numero} NO cambio de estado.`);
    }
  }

  return (
    <li className="rounded-xl border border-border bg-card p-4">
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-mono text-xl font-semibold tabular-nums">#{comanda.numero}</span>
        <span className="text-sm text-muted-foreground">
          {comanda.mesaNumero ? `Mesa ${comanda.mesaNumero}` : (comanda.etiqueta ?? 'Sin mesa')}
        </span>
        {/* Cuenta en local, con un temporizador. Una peticion por segundo para
            mover un contador seria la mas cara y la mas inutil del sistema. */}
        <Transcurrido desde={comanda.ocurrioEn} />
      </div>

      <ul className="mt-3 space-y-1.5 text-sm">
        {comanda.lineas.map((linea) => (
          <li key={linea.id} className="flex gap-2">
            <span className="font-mono tabular-nums text-muted-foreground">
              {linea.cantidad}&times;
            </span>
            <span className="min-w-0">
              {linea.producto}
              {linea.notas && (
                <span className="block text-xs text-warning">{linea.notas}</span>
              )}
            </span>
          </li>
        ))}
      </ul>

      <Button
        size="key"
        className="mt-4 w-full"
        disabled={enviando}
        onClick={avanzar}
        // `estacion` viaja para que el boton no cambie de sitio al refrescar
        // con filtro puesto.
        data-estacion={estacion}
      >
        {enviando ? 'Guardando...' : accion}
      </Button>
    </li>
  );
}

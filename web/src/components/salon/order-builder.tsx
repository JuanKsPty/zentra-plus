'use client';

import { MinusIcon, PlusIcon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Dinero } from '@/components/shared/money';
import { cn } from '@/lib/utils';
import { reportar } from '@/lib/errores';
import type { Categoria, Producto } from '@/services/catalogService';
import { tomarComanda } from '@/services/ordersService';

interface EnLaComanda {
  producto: Producto;
  cantidad: number;
}

export function ArmarComanda({
  mesaId,
  mesaNumero,
  categorias,
  productos,
}: {
  mesaId: string | null;
  mesaNumero: number | null;
  categorias: Categoria[];
  productos: Producto[];
}) {
  const router = useRouter();
  const [seccion, setSeccion] = useState<string | null>(null);
  const [enComanda, setEnComanda] = useState<EnLaComanda[]>([]);
  const [enviando, setEnviando] = useState(false);

  const visibles = useMemo(
    () => (seccion ? productos.filter((p) => p.categoriaId === seccion) : productos),
    [productos, seccion],
  );

  // El subtotal se calcula aqui SOLO para que el mesero lo vea mientras arma.
  // El total autoritativo lo pone el servidor con el precio de la sucursal: un
  // importe calculado en el dispositivo es un importe con un precio que puede
  // estar viejo.
  const avance = enComanda.reduce((suma, linea) => suma + linea.producto.precio * linea.cantidad, 0);

  function anadir(producto: Producto) {
    setEnComanda((actual) => {
      const ya = actual.find((l) => l.producto.id === producto.id);
      if (ya) {
        return actual.map((l) =>
          l.producto.id === producto.id ? { ...l, cantidad: l.cantidad + 1 } : l,
        );
      }
      return [...actual, { producto, cantidad: 1 }];
    });
  }

  function quitar(productoId: string) {
    setEnComanda((actual) =>
      actual
        .map((l) => (l.producto.id === productoId ? { ...l, cantidad: l.cantidad - 1 } : l))
        .filter((l) => l.cantidad > 0),
    );
  }

  async function enviar() {
    setEnviando(true);
    try {
      const comanda = await tomarComanda({
        mesaId,
        etiqueta: mesaId ? undefined : 'Para llevar',
        lineas: enComanda.map((l) => ({ productoId: l.producto.id, cantidad: l.cantidad })),
      });
      toast.success(`Comanda #${comanda.numero} enviada a cocina`);
      router.push(`/comanda/${comanda.id}`);
      router.refresh();
    } catch (error) {
      setEnviando(false);
      // Lo que se armo NO se pierde: el estado sigue en pantalla y se puede
      // reenviar. Decirlo evita que el mesero la teclee otra vez desde cero.
      reportar(error, 'La comanda NO llego a cocina. Vuelve a enviarla.');
    }
  }

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      <div className="min-w-0 flex-1 space-y-4">
        <h1 className="font-heading text-xl font-semibold tracking-tight">
          {mesaNumero ? `Mesa ${mesaNumero}` : 'Para llevar'}
        </h1>

        <div className="flex flex-wrap gap-2">
          <Seccion activa={seccion === null} onClick={() => setSeccion(null)}>
            Todo
          </Seccion>
          {categorias.map((categoria) => (
            <Seccion
              key={categoria.id}
              activa={seccion === categoria.id}
              onClick={() => setSeccion(categoria.id)}
            >
              {categoria.nombre}
            </Seccion>
          ))}
        </div>

        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {visibles.map((producto) => (
            <li key={producto.id}>
              <button
                type="button"
                onClick={() => anadir(producto)}
                className="flex min-h-20 w-full flex-col items-start justify-between gap-2 rounded-xl border border-border bg-card p-3 text-left transition-colors hover:bg-accent"
              >
                <span className="text-sm font-medium">{producto.nombre}</span>
                <Dinero centavos={producto.precio} className="text-sm text-muted-foreground" />
              </button>
            </li>
          ))}
        </ul>
      </div>

      <aside className="w-full shrink-0 space-y-3 lg:w-80">
        <div className="rounded-xl border border-border bg-card">
          {enComanda.length === 0 ? (
            <p className="p-4 text-sm text-muted-foreground">
              Toca un producto para anadirlo.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {enComanda.map((linea) => (
                <li key={linea.producto.id} className="flex items-center gap-2 p-3">
                  <span className="min-w-0 flex-1 text-sm">{linea.producto.nombre}</span>
                  <Button
                    variant="ghost"
                    size="icon-touch"
                    aria-label={`Quitar uno de ${linea.producto.nombre}`}
                    onClick={() => quitar(linea.producto.id)}
                  >
                    <MinusIcon />
                  </Button>
                  <span className="w-6 text-center font-mono tabular-nums">{linea.cantidad}</span>
                  <Button
                    variant="ghost"
                    size="icon-touch"
                    aria-label={`Anadir uno de ${linea.producto.nombre}`}
                    onClick={() => anadir(linea.producto)}
                  >
                    <PlusIcon />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex items-baseline justify-between px-1">
          <span className="text-sm text-muted-foreground">Subtotal</span>
          <Dinero centavos={avance} className="text-xl font-semibold" />
        </div>

        <Button
          size="key"
          className="w-full"
          disabled={enComanda.length === 0 || enviando}
          onClick={enviar}
        >
          {enviando ? 'Enviando...' : 'Enviar a cocina'}
        </Button>
      </aside>
    </div>
  );
}

function Seccion({
  activa,
  children,
  ...resto
}: { activa: boolean } & React.ComponentProps<'button'>) {
  return (
    <button
      type="button"
      className={cn(
        'h-11 rounded-lg border px-4 text-sm transition-colors',
        activa
          ? 'border-primary bg-primary text-primary-foreground'
          : 'border-border bg-card hover:bg-accent',
      )}
      {...resto}
    >
      {children}
    </button>
  );
}

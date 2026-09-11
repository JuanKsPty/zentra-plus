import { cn } from '@/lib/utils';

/**
 * Un listado que se renderiza DOS VECES: tarjetas en movil, tabla en escritorio.
 *
 * No es lujo. Una tabla de cinco columnas en los 358 px utiles de un telefono
 * ensena columna y media: para ver el precio hay que desplazar a ciegas una
 * franja que no parece desplazable, y el boton de editar queda fuera de
 * pantalla. Eso no es denso, es inservible — y el dueno abre el panel desde el
 * telefono varias veces al dia.
 *
 * El escalon se escribe AQUI, una vez, para que no derive pantalla por pantalla.
 */

export function ListaDeTarjetas({ className, ...resto }: React.ComponentProps<'ul'>) {
  return <ul className={cn('flex flex-col gap-3 sm:hidden', className)} {...resto} />;
}

export function Tarjeta({ className, ...resto }: React.ComponentProps<'li'>) {
  return (
    <li
      className={cn('rounded-xl border border-border bg-card p-4 text-sm', className)}
      {...resto}
    />
  );
}

export function MarcoDeTabla({ className, ...resto }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn('hidden overflow-hidden rounded-xl border border-border sm:block', className)}
      {...resto}
    />
  );
}

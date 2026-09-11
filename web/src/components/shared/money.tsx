import { formatearDinero } from '@/lib/money';
import { cn } from '@/lib/utils';

/**
 * Un importe.
 *
 * Existe como componente —y no como una clase que cada pantalla recuerda— por
 * `tabular-nums`: sin el, una columna de precios BAILA de ancho al actualizarse
 * y deja de poder leerse en vertical. Confiar en que treinta pantallas lo
 * escriban bien es confiar de mas.
 */
export function Dinero({
  centavos,
  moneda,
  className,
  ...resto
}: { centavos: number; moneda?: string } & React.ComponentProps<'span'>) {
  return (
    <span className={cn('font-mono tabular-nums', className)} {...resto}>
      {formatearDinero(centavos, moneda)}
    </span>
  );
}

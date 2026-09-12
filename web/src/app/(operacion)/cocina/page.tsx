import { AvisoDeFallo } from '@/components/shared/api-error-notice';
import { esFalloDeApi } from '@/lib/errores';
import { Refrescador } from '@/components/realtime/realtime-refresher';
import { SinNada } from '@/components/shared/empty-state';
import { Tablero } from '@/components/cocina/kds-board';
import { tablero } from '@/services/ordersService.server';

export const metadata = { title: 'Cocina · Zentra+' };

export default async function Cocina({
  searchParams,
}: {
  searchParams: Promise<{ estacion?: string }>;
}) {
  const { estacion } = await searchParams;

  let comandas;
  try {
    comandas = await tablero(estacion);
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  return (
    <>
      <Refrescador eventos={['order.created', 'order.changed']} />

      {comandas.length === 0 ? (
        <SinNada
          titulo="Nada en cola"
          descripcion="Las comandas nuevas aparecen aqui solas, sin recargar."
        />
      ) : (
        <Tablero comandas={comandas} estacion={estacion} />
      )}
    </>
  );
}

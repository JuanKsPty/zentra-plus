import { notFound } from 'next/navigation';

import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { PantallaDeCobro } from '@/components/caja/checkout';
import { ApiError } from '@/services/http';
import { estadoDeCobro, metodosDeCobro, turnoActual } from '@/services/cashService.server';
import { verComanda } from '@/services/ordersService.server';

export const metadata = { title: 'Cobrar · Zentra+' };

export default async function Cobro({ params }: { params: Promise<{ ordenId: string }> }) {
  const { ordenId } = await params;

  let datos;
  try {
    const [comanda, estado, metodos, turno] = await Promise.all([
      verComanda(ordenId),
      estadoDeCobro(ordenId),
      metodosDeCobro(),
      turnoActual(),
    ]);
    datos = { comanda, estado, metodos, turno };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) notFound();
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  return (
    <PantallaDeCobro
      comanda={datos.comanda}
      inicial={datos.estado}
      metodos={datos.metodos}
      hayTurno={datos.turno !== null}
    />
  );
}

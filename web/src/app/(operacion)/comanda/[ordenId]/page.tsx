import { notFound } from 'next/navigation';

import { AvisoDeFallo } from '@/components/shared/api-error-notice';
import { esFalloDeApi } from '@/lib/errores';
import { Refrescador } from '@/components/realtime/realtime-refresher';
import { DetalleDeComanda } from '@/components/salon/order-detail';
import { ApiError } from '@/services/http';
import { verComanda } from '@/services/ordersService.server';

export const metadata = { title: 'Comanda · Zentra+' };

export default async function Comanda({ params }: { params: Promise<{ ordenId: string }> }) {
  const { ordenId } = await params;

  let comanda;
  try {
    comanda = await verComanda(ordenId);
  } catch (error) {
    // `notFound()` SOLO cuando la API dice 404 de verdad. Si el fetch rechazo,
    // «no existe» y «no pudimos preguntar» son cosas distintas y llevan a
    // acciones distintas.
    if (error instanceof ApiError && error.status === 404) notFound();
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  return (
    <>
      <Refrescador eventos={['order.changed']} />
      <DetalleDeComanda comanda={comanda} />
    </>
  );
}

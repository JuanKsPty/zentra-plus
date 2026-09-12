import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { SinNada } from '@/components/shared/empty-state';
import { Refrescador } from '@/components/realtime/realtime-refresher';
import { SalonEnVivo } from '@/components/salon/floor-view';
import { listarAbiertas } from '@/services/ordersService.server';
import { listarMesas, listarZonas } from '@/services/floorService';

export const metadata = { title: 'Salon · Zentra+' };

export default async function Salon() {
  let datos;
  try {
    const [zonas, mesas, comandas] = await Promise.all([
      listarZonas(),
      listarMesas(),
      listarAbiertas(),
    ]);
    datos = { zonas, mesas, comandas };
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  return (
    <>
      {/* Dos eventos: la comanda cambia y la mesa cambia. Una sola accion
          humana dispara los dos, y el rebote del refrescador los junta. */}
      <Refrescador eventos={['order.created', 'order.changed', 'table.changed']} />

      {datos.mesas.length === 0 ? (
        <SinNada
          titulo="Este salon no tiene mesas"
          descripcion="Se crean desde el panel, en Mesas."
        />
      ) : (
        <SalonEnVivo zonas={datos.zonas} mesas={datos.mesas} comandas={datos.comandas} />
      )}
    </>
  );
}

import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { CabeceraDePagina } from '@/components/shared/page-header';
import { SinNada } from '@/components/shared/empty-state';
import { MapaDelSalon } from '@/components/panel/floor-map';
import { listarMesas, listarZonas } from '@/services/floorService';

export const metadata = { title: 'Mesas · Zentra+' };

export default async function Mesas() {
  let datos;
  try {
    const [zonas, mesas] = await Promise.all([listarZonas(), listarMesas()]);
    datos = { zonas, mesas };
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return (
      <div className="space-y-6">
        <CabeceraDePagina titulo="Mesas" />
        <AvisoDeFallo error={error} />
      </div>
    );
  }

  const { zonas, mesas } = datos;

  return (
    <div className="space-y-6">
      <CabeceraDePagina
        titulo="Mesas"
        descripcion="El salon de esta sucursal. Cada sede numera sus mesas desde uno."
      />

      {mesas.length === 0 ? (
        <SinNada
          titulo="Todavia no hay mesas"
          descripcion="Crea una zona y dale mesas para poder tomar comandas."
        />
      ) : (
        <MapaDelSalon zonas={zonas} mesas={mesas} />
      )}
    </div>
  );
}

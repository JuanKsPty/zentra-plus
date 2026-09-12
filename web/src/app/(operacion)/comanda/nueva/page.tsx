import { notFound } from 'next/navigation';

import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { SinNada } from '@/components/shared/empty-state';
import { ArmarComanda } from '@/components/salon/order-builder';
import { listarCategorias, listarProductos } from '@/services/catalogService';
import { listarMesas } from '@/services/floorService';

export const metadata = { title: 'Nueva comanda · Zentra+' };

/**
 * Tomar una comanda.
 *
 * Esta carpeta tiene que existir aunque estuviera vacia: sin ella, `/comanda/nueva`
 * lo captura la ruta dinamica `[ordenId]` y el mesero ve un 404 al tocar una
 * mesa libre. Next prioriza el segmento literal, pero solo si el segmento
 * literal existe.
 */
export default async function NuevaComanda({
  searchParams,
}: {
  searchParams: Promise<{ mesa?: string }>;
}) {
  const { mesa: mesaId } = await searchParams;

  let datos;
  try {
    const [productos, categorias, mesas] = await Promise.all([
      listarProductos({ page: 1 }),
      listarCategorias(),
      listarMesas(),
    ]);
    datos = { productos: productos.items, categorias, mesas };
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return <AvisoDeFallo error={error} />;
  }

  const mesa = mesaId ? datos.mesas.find((m) => m.id === mesaId) : undefined;
  if (mesaId && !mesa) notFound();

  const disponibles = datos.productos.filter((p) => p.disponible);

  if (disponibles.length === 0) {
    return (
      <SinNada
        titulo="No hay nada disponible en la carta"
        descripcion="Comprueba el catalogo de esta sucursal desde el panel."
      />
    );
  }

  return (
    <ArmarComanda
      mesaId={mesa?.id ?? null}
      mesaNumero={mesa?.numero ?? null}
      categorias={datos.categorias}
      productos={disponibles}
    />
  );
}

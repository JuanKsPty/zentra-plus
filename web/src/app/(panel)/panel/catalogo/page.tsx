import { CabeceraDePagina } from '@/components/shared/page-header';
import { AvisoDeFallo, esFalloDeApi } from '@/components/shared/api-error-notice';
import { SinNada } from '@/components/shared/empty-state';
import { TablaDeProductos } from '@/components/panel/product-table';
import { FiltroDeCarta } from '@/components/panel/catalog-filter';
import { listarCategorias, listarProductos } from '@/services/catalogService';

export const metadata = { title: 'Catalogo · Zentra+' };

export default async function Catalogo({
  searchParams,
}: {
  searchParams: Promise<{ q?: string; categoria?: string }>;
}) {
  const filtro = await searchParams;

  let datos;
  try {
    const [productos, categorias] = await Promise.all([
      listarProductos({ q: filtro.q, categoria: filtro.categoria }),
      listarCategorias(),
    ]);
    datos = { productos, categorias };
  } catch (error) {
    if (!esFalloDeApi(error)) throw error;
    return (
      <div className="space-y-6">
        <CabeceraDePagina titulo="Catalogo" />
        <AvisoDeFallo error={error} />
      </div>
    );
  }

  const { productos, categorias } = datos;
  const nombrePorCategoria = new Map(categorias.map((c) => [c.id, c.nombre]));

  return (
    <div className="space-y-6">
      <CabeceraDePagina
        titulo="Catalogo"
        descripcion="La carta es del negocio. El precio y la disponibilidad son de esta sucursal."
      />

      <FiltroDeCarta categorias={categorias} />

      {productos.items.length === 0 ? (
        <SinNada
          titulo={filtro.q ? 'Nada coincide con esa busqueda' : 'Todavia no hay productos'}
          descripcion={
            filtro.q
              ? 'Prueba con otra palabra o quita el filtro.'
              : 'Los productos que crees aqui se ven en todas las sucursales.'
          }
        />
      ) : (
        <>
          <TablaDeProductos productos={productos.items} categorias={nombrePorCategoria} />
          {/* El total, no un corte silencioso: «mostrando 50 de 312» es
              informacion; truncar sin decirlo se lee como «esto es todo». */}
          <p className="text-xs text-muted-foreground">
            Mostrando {productos.items.length} de {productos.total}
          </p>
        </>
      )}
    </div>
  );
}

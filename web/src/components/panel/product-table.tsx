import { Badge } from '@/components/ui/badge';
import { ListaDeTarjetas, MarcoDeTabla, Tarjeta } from '@/components/shared/data-list';
import { Dinero } from '@/components/shared/money';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { Producto } from '@/services/catalogService';

const ESTACIONES: Record<string, string> = {
  kitchen: 'Cocina',
  bar: 'Barra',
  immediate: 'Entrega directa',
};

export function TablaDeProductos({
  productos,
  categorias,
}: {
  productos: Producto[];
  categorias: Map<string, string>;
}) {
  return (
    <>
      <ListaDeTarjetas>
        {productos.map((producto) => (
          <Tarjeta key={producto.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate font-medium">{producto.nombre}</p>
                <p className="text-xs text-muted-foreground">
                  {categorias.get(producto.categoriaId ?? '') ?? 'Sin seccion'} ·{' '}
                  {ESTACIONES[producto.estacion] ?? producto.estacion}
                </p>
              </div>
              <Dinero centavos={producto.precio} className="shrink-0 font-medium" />
            </div>
            <div className="mt-3 flex gap-2">
              <EstadoDeProducto producto={producto} />
            </div>
          </Tarjeta>
        ))}
      </ListaDeTarjetas>

      <MarcoDeTabla>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Producto</TableHead>
              <TableHead>Seccion</TableHead>
              <TableHead>Donde se prepara</TableHead>
              <TableHead className="text-right">Precio aqui</TableHead>
              <TableHead>Estado</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {productos.map((producto) => (
              <TableRow key={producto.id}>
                <TableCell className="font-medium">{producto.nombre}</TableCell>
                <TableCell className="text-muted-foreground">
                  {categorias.get(producto.categoriaId ?? '') ?? 'Sin seccion'}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {ESTACIONES[producto.estacion] ?? producto.estacion}
                </TableCell>
                <TableCell className="text-right">
                  <Dinero centavos={producto.precio} />
                  {producto.precio !== producto.precioBase && (
                    <span className="ml-2 text-xs text-muted-foreground">
                      (base <Dinero centavos={producto.precioBase} />)
                    </span>
                  )}
                </TableCell>
                <TableCell>
                  <EstadoDeProducto producto={producto} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </MarcoDeTabla>
    </>
  );
}

function EstadoDeProducto({ producto }: { producto: Producto }) {
  // Relleno tenue = estado. El relleno solido se reserva para lo que se pulsa.
  if (!producto.activo) {
    return (
      <Badge className="border-muted-foreground/25 bg-muted text-muted-foreground">
        Retirado
      </Badge>
    );
  }
  if (!producto.disponible) {
    return (
      <Badge className="border-warning/25 bg-warning/12 text-warning">Hoy no queda</Badge>
    );
  }
  return <Badge className="border-success/25 bg-success/12 text-success">En carta</Badge>;
}

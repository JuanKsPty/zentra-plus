import { describirFallo } from '@/lib/errores';

/**
 * Lo que se pinta cuando una pantalla no pudo cargar.
 *
 * NO se pinta una lista vacia. Un listado sin datos y un listado que no cargo
 * se ven igual, y asi es como un mesero ve «no hay comandas» cuando lo que hay
 * es un cable suelto. Las dos lecturas llevan a acciones opuestas: una es
 * esperar, la otra es ir a mirar el router.
 *
 * QUE dice cada fallo no se decide aqui: se decide en `lib/errores.ts`, que es
 * el mismo sitio del que salen los avisos flotantes de los botones. Esta pieza
 * solo lo pinta, para que la pantalla y el toast no puedan contar dos versiones
 * distintas del mismo corte de red.
 */
export function AvisoDeFallo({ error }: { error: unknown }) {
  const fallo = describirFallo(error);

  // Ninguna pantalla deberia llegar aqui con otra cosa —todas comprueban
  // `esFalloDeApi` antes—, pero si pasa se relanza en vez de inventar un texto:
  // lo recoge `error.tsx`, con su traza y su «Reintentar».
  if (!fallo) throw error;

  return (
    <div className="rounded-xl border border-destructive/30 bg-destructive/10 px-5 py-4">
      <p className="text-sm font-medium text-destructive">{fallo.titulo}</p>
      <p className="mt-1 text-sm text-muted-foreground">
        {fallo.pista ? `${fallo.mensaje} ${fallo.pista}` : fallo.mensaje}
      </p>
      {/* La referencia es lo unico que enlaza esta pantalla con la linea del
          log del servidor. En produccion el mensaje puede ser generico; esto
          no. */}
      {fallo.referencia && (
        <p className="mt-2 font-mono text-xs text-muted-foreground">
          Referencia: {fallo.referencia}
        </p>
      )}
    </div>
  );
}

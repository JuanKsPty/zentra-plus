'use client';

import { Button } from '@/components/ui/button';

/**
 * Un fallo dentro de una pantalla queda CONTENIDO aqui.
 *
 * Sin este archivo, cualquier excepcion sube hasta `global-error` y se lleva por
 * delante la cascara entera. Con el, el layout sigue en pie y hay un
 * «Reintentar» que no recarga la pagina — en una tableta a media comanda, eso
 * es la diferencia entre seguir trabajando y volver a entrar.
 */
export default function ErrorDePantalla({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center gap-4 py-16 text-center">
      <h1 className="font-heading text-lg font-semibold">Algo se rompio en esta pantalla</h1>
      <p className="text-sm text-muted-foreground">
        El resto del sistema sigue funcionando. Puedes reintentar sin volver a entrar.
      </p>
      <Button onClick={reset} size="touch">
        Reintentar
      </Button>
      {/* En produccion el mensaje no se envia al navegador; el `digest` es lo
          unico que enlaza esta pantalla con la traza del servidor. */}
      {error.digest && (
        <p className="font-mono text-xs text-muted-foreground">Referencia: {error.digest}</p>
      )}
    </div>
  );
}

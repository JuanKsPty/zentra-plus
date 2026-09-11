import Link from 'next/link';

import { Button } from '@/components/ui/button';

/**
 * Sin este archivo, `notFound()` pinta el fallback interno de Next, que trae un
 * `<style>` en linea con `body{color:#000;background:#fff}`: PISA EL TEMA —un
 * blanco cegador en una cocina de noche— y sale en ingles dentro de una
 * aplicacion con `lang="es"`.
 */
export default function NoEncontrado() {
  return (
    <div className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-4 px-6 text-center">
      <p className="font-mono text-sm text-muted-foreground">404</p>
      <h1 className="font-heading text-xl font-semibold tracking-tight">
        Esta pantalla no existe
      </h1>
      <p className="text-sm text-muted-foreground">
        Puede que el enlace este viejo o que lo que buscabas se haya borrado.
      </p>
      <Button size="touch" nativeButton={false} render={<Link href="/" />}>
        Volver al inicio
      </Button>
    </div>
  );
}

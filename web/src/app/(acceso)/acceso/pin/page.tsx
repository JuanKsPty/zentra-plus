import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { ApiError, NetworkError } from '@/services/http';
import { listarOperativos } from '@/services/usersService';

export const metadata = { title: 'Entrar con PIN · Zentra+' };

/**
 * La rejilla de «quien eres».
 *
 * Es publica a proposito: hay que verla ANTES de tener sesion, porque es como
 * se elige el usuario. Lo que protege la cuenta es el PIN, no que el nombre
 * este escondido — y ocultar la lista obligaria a teclear un identificador que
 * nadie recuerda.
 */
export default async function ElegirQuienEres() {
  let personas;
  try {
    personas = await listarOperativos();
  } catch (error) {
    const sinRed = error instanceof NetworkError;
    if (!sinRed && !(error instanceof ApiError)) throw error;
    return (
      <Aviso
        texto={
          sinRed
            ? 'No hay conexion con el servidor. Comprueba la red del local.'
            : 'El servidor no pudo dar la lista. Intenta de nuevo en un momento.'
        }
      />
    );
  }

  if (personas.length === 0) {
    return <Aviso texto="Todavia no hay nadie con PIN. Configuralo desde el panel." />;
  }

  return (
    <div className="w-full max-w-md space-y-4">
      <p className="text-center text-sm text-muted-foreground">Toca tu nombre</p>
      <ul className="grid grid-cols-2 gap-3">
        {personas.map((persona) => (
          <li key={persona.id}>
            <Button
              variant="outline"
              size="touch"
              nativeButton={false}
              className="h-auto w-full flex-col items-start gap-0.5 py-3 text-left"
              render={<Link href={`/acceso/pin/${persona.id}`} />}
            >
              <span className="font-medium">{persona.name}</span>
              <span className="text-xs text-muted-foreground">
                {persona.roleName ?? 'Sin puesto'}
              </span>
            </Button>
          </li>
        ))}
      </ul>
      <p className="text-center text-sm text-muted-foreground">
        <Link href="/acceso" className="text-primary underline-offset-4 hover:underline">
          Entrar con correo
        </Link>
      </p>
    </div>
  );
}

function Aviso({ texto }: { texto: string }) {
  return (
    <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 text-center">
      <p className="text-sm text-muted-foreground">{texto}</p>
      <Button
        variant="outline"
        size="touch"
        className="mt-4"
        nativeButton={false}
        render={<Link href="/acceso" />}
      >
        Entrar con correo
      </Button>
    </div>
  );
}

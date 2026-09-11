import { NOMBRE_PRODUCTO } from '@/lib/env';
import { ApiError, NetworkError } from '@/services/http';
import { obtenerSalud } from '@/services/systemService';

/**
 * La primera pantalla no es un saludo: comprueba que el frontend y la API se
 * estan hablando. Es lo que dice de un vistazo si `docker compose up` dejo
 * todo en pie, sin abrir una terminal.
 */
export default async function Inicio() {
  const estado = await leerEstado();

  return (
    <main className="mx-auto flex min-h-dvh max-w-2xl flex-col justify-center gap-8 px-6 py-12">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">{NOMBRE_PRODUCTO}</h1>
        <p className="text-sm text-muted-foreground">
          Gestion operativa multisucursal para restaurantes, bares y cafeterias.
        </p>
      </header>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Estado de la API
        </h2>

        {estado.tipo === 'ok' ? (
          <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <Dato etiqueta="Estado" valor={estado.salud.status} destacado />
            <Dato etiqueta="Entorno" valor={estado.salud.environment} />
            <Dato etiqueta="Servicio" valor={estado.salud.app} />
            <Dato etiqueta="Version" valor={estado.salud.version} />
          </dl>
        ) : (
          <p className="mt-4 text-sm text-destructive">{estado.mensaje}</p>
        )}
      </section>
    </main>
  );
}

function Dato({
  etiqueta,
  valor,
  destacado = false,
}: {
  etiqueta: string;
  valor: string;
  destacado?: boolean;
}) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className={`font-mono text-sm ${destacado ? 'text-success' : ''}`}>{valor}</dd>
    </div>
  );
}

type Estado = { tipo: 'ok'; salud: Awaited<ReturnType<typeof obtenerSalud>> } | { tipo: 'fallo'; mensaje: string };

async function leerEstado(): Promise<Estado> {
  try {
    return { tipo: 'ok', salud: await obtenerSalud() };
  } catch (error) {
    // «No hay red» y «el servidor contesto que no» llevan a acciones distintas,
    // asi que no se pintan con el mismo mensaje.
    if (error instanceof NetworkError) {
      return {
        tipo: 'fallo',
        mensaje: 'No se pudo contactar con la API. Comprueba que este levantada: pnpm dev',
      };
    }
    if (error instanceof ApiError) {
      return { tipo: 'fallo', mensaje: `La API respondio ${error.status}: ${error.message}` };
    }
    throw error;
  }
}

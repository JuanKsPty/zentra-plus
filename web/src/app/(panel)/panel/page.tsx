import { obtenerSesion } from '@/lib/auth/session';

export default async function Resumen() {
  const sesion = await obtenerSesion();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="font-heading text-xl font-semibold tracking-tight">Resumen</h1>
        <p className="text-sm text-muted-foreground">
          Hola, {sesion?.name}. Las metricas del dia llegan con la fase de reportes.
        </p>
      </header>

      <section className="rounded-xl border border-border bg-card p-5">
        <h2 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Tu sesion
        </h2>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <Dato etiqueta="Puesto" valor={sesion?.roleName ?? 'Sin puesto'} />
          <Dato etiqueta="Entraste por" valor={sesion?.loginMethod === 'pin' ? 'PIN' : 'Correo'} />
          <Dato etiqueta="Permisos" valor={String(sesion?.permissions.length ?? 0)} />
          <Dato etiqueta="Sucursales" valor={String(sesion?.branchIds.length ?? 0)} />
        </dl>
      </section>
    </div>
  );
}

function Dato({ etiqueta, valor }: { etiqueta: string; valor: string }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
      <dd className="font-mono tabular-nums">{valor}</dd>
    </div>
  );
}

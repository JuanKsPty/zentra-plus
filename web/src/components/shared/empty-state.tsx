export function SinNada({
  titulo,
  descripcion,
  children,
}: {
  titulo: string;
  descripcion?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-dashed border-border px-6 py-12 text-center">
      <p className="font-medium">{titulo}</p>
      {descripcion && <p className="mt-1 text-sm text-muted-foreground">{descripcion}</p>}
      {children && <div className="mt-4 flex justify-center">{children}</div>}
    </div>
  );
}

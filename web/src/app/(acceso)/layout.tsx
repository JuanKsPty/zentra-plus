export default function LayoutDeAcceso({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-8 px-6 py-12">
      <div className="text-center">
        <h1 className="font-heading text-2xl font-semibold tracking-tight">Zentra+</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Gestion operativa para restaurantes, bares y cafeterias
        </p>
      </div>
      {children}
    </div>
  );
}

import Link from 'next/link';
import { notFound } from 'next/navigation';

import { TecladoDePin } from '@/components/acceso/pin-pad';
import { Button } from '@/components/ui/button';
import { listarOperativos } from '@/services/usersService';

export const metadata = { title: 'Tu PIN · Zentra+' };

export default async function PedirPin({
  params,
}: {
  params: Promise<{ empleadoId: string }>;
}) {
  const { empleadoId } = await params;
  const personas = await listarOperativos();
  const persona = personas.find((p) => p.id === empleadoId);

  // Un id que no esta en la lista no existe para esta pantalla. Es un 404 y no
  // un formulario vacio: pedir un PIN de alguien que no puede entrar por PIN
  // solo sirve para que el operario lo teclee tres veces.
  if (!persona) notFound();

  return (
    <div className="flex w-full flex-col items-center gap-6">
      <TecladoDePin empleadoId={persona.id} nombre={persona.name} />
      <Button variant="ghost" size="touch" nativeButton={false} render={<Link href="/acceso/pin" />}>
        No soy yo
      </Button>
    </div>
  );
}

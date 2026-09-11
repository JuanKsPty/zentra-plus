'use client';

import { MoonIcon, SunIcon } from 'lucide-react';
import { useTheme } from 'next-themes';

import { Button } from '@/components/ui/button';

/**
 * Cambia entre claro y oscuro.
 *
 * Se pintan LOS DOS iconos y elige el CSS con la variante `dark:`. El patron
 * habitual —un estado `montado` puesto desde un efecto— existe para evitar el
 * desajuste de hidratacion, pero cuesta un render extra y deja el icono
 * equivocado durante un instante. Aqui el servidor y el cliente emiten
 * exactamente lo mismo y la clase del tema, que next-themes escribe en `<html>`
 * antes de hidratar, decide cual se ve.
 */
export function InterruptorDeTema() {
  const { resolvedTheme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      aria-label="Cambiar entre tema claro y oscuro"
      onClick={() => setTheme(resolvedTheme === 'dark' ? 'light' : 'dark')}
    >
      <MoonIcon className="dark:hidden" />
      <SunIcon className="hidden dark:block" />
    </Button>
  );
}

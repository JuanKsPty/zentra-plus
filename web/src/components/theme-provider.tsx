'use client';

import { ThemeProvider as ProveedorDeTema } from 'next-themes';

export function ProveedorTema({ children }: { children: React.ReactNode }) {
  return (
    <ProveedorDeTema
      attribute="class"
      defaultTheme="system"
      enableSystem
      // Sin esto, cambiar de tema anima cada color de la pantalla a la vez y el
      // salto se ve como un parpadeo.
      disableTransitionOnChange
    >
      {children}
    </ProveedorDeTema>
  );
}

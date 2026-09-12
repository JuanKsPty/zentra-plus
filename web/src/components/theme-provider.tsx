'use client';

import { ThemeProvider as ProveedorDeTema } from 'next-themes';

export function ProveedorTema({
  children,
  nonce,
}: {
  children: React.ReactNode;
  // El nonce de la CSP. `next-themes` pone un script EN LINEA para aplicar el
  // tema antes del primer pintado, y sin firmarlo la politica lo bloquea: la
  // pantalla arranca en claro y salta al oscuro al hidratar, sin un solo error
  // que lo explique.
  nonce?: string;
}) {
  return (
    <ProveedorDeTema
      attribute="class"
      defaultTheme="system"
      enableSystem
      nonce={nonce}
      // Sin esto, cambiar de tema anima cada color de la pantalla a la vez y el
      // salto se ve como un parpadeo.
      disableTransitionOnChange
    >
      {children}
    </ProveedorDeTema>
  );
}

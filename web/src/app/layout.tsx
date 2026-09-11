import type { Metadata } from 'next';
import { IBM_Plex_Mono, IBM_Plex_Sans, IBM_Plex_Sans_Condensed } from 'next/font/google';

import { ProveedorTema } from '@/components/theme-provider';
import { Toaster } from '@/components/ui/sonner';

import { NOMBRE_PRODUCTO } from '@/lib/env';

import './globals.css';

// IBM Plex y no una grotesca cualquiera: es tipografia de instrumentacion, con
// cifras tabulares de verdad y una mono hermana que casa. La mono es para el
// dinero, las cantidades y los numeros de cuenta.
const sans = IBM_Plex_Sans({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-sans',
});
// La condensada da caracter propio y, sobre todo, AHORRA ANCHO: en los 358 px
// utiles de un telefono, un titulo de cinco palabras deja de partirse.
const heading = IBM_Plex_Sans_Condensed({
  subsets: ['latin'],
  weight: ['600', '700'],
  variable: '--font-heading',
});
const mono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-mono',
});

export const metadata: Metadata = {
  title: NOMBRE_PRODUCTO,
  description: 'Gestion operativa multisucursal para restaurantes, bares y cafeterias',
  icons: { icon: '/favicon.svg' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // suppressHydrationWarning: next-themes escribe la clase del tema en <html>
    // antes de que React hidrate, asi que servidor y cliente no coinciden a
    // proposito. Es el unico sitio donde esa diferencia es correcta.
    <html
      lang="es"
      suppressHydrationWarning
      className={`${sans.variable} ${heading.variable} ${mono.variable}`}
    >
      <body className="min-h-dvh font-sans antialiased">
        <ProveedorTema>
          {children}
          <Toaster />
        </ProveedorTema>
      </body>
    </html>
  );
}

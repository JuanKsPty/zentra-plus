import type { Metadata } from 'next';
import { IBM_Plex_Mono, IBM_Plex_Sans } from 'next/font/google';

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
    <html lang="es" className={`${sans.variable} ${mono.variable}`}>
      <body className="min-h-dvh font-sans antialiased">{children}</body>
    </html>
  );
}

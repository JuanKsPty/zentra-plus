import { BookOpenIcon, GaugeIcon, GridIcon, type LucideIcon } from 'lucide-react';

import type { Permiso } from '@/config/permissions';

/**
 * La UNICA fuente de destinos del panel.
 *
 * Sin `'use client'`, para que la importen a la vez el layout de servidor, la
 * barra lateral y la barra inferior del movil. Dos listas derivando es
 * exactamente como una barra acaba mostrando un enlace que devuelve 403.
 *
 * REGLA: un destino se anade EN EL MISMO COMMIT que su pantalla, nunca antes.
 * Una barra que ofrece enlaces a pantallas que no existen es un 404 que solo se
 * descubre pulsandolo, y `navigation.spec.ts` lo comprueba contra las carpetas
 * reales de `app/(panel)`.
 */

export interface Destino {
  id: string;
  etiqueta: string;
  href: string;
  icono: LucideIcon;
  permiso: Permiso;
  grupo: 'operacion' | 'negocio' | 'configuracion';
  /**
   * Posicion en la barra inferior del telefono. Sin valor, solo aparece en el
   * cajon. Caben cuatro: el quinto hueco es siempre «Mas».
   */
  barra?: 1 | 2 | 3 | 4;
}

export const DESTINOS: Destino[] = [
  {
    id: 'resumen',
    etiqueta: 'Resumen',
    href: '/panel',
    icono: GaugeIcon,
    permiso: 'reports:read',
    grupo: 'operacion',
    barra: 1,
  },
  {
    id: 'catalogo',
    etiqueta: 'Catalogo',
    href: '/panel/catalogo',
    icono: BookOpenIcon,
    permiso: 'catalog:read',
    grupo: 'negocio',
    barra: 2,
  },
  {
    id: 'mesas',
    etiqueta: 'Mesas',
    href: '/panel/mesas',
    icono: GridIcon,
    permiso: 'floor:read',
    grupo: 'negocio',
    barra: 3,
  },
];

export const ETIQUETAS_DE_GRUPO: Record<Destino['grupo'], string> = {
  operacion: 'Operacion',
  negocio: 'Negocio',
  configuracion: 'Configuracion',
};

export function destinosPara(permisos: readonly string[]): Destino[] {
  return DESTINOS.filter((destino) => permisos.includes(destino.permiso));
}

export function destinosDeBarraPara(permisos: readonly string[]): Destino[] {
  return destinosPara(permisos)
    .filter((destino) => destino.barra !== undefined)
    .sort((a, b) => (a.barra ?? 0) - (b.barra ?? 0))
    .slice(0, 4);
}

/**
 * `/panel` es prefijo de todo lo demas, asi que solo se marca activo cuando la
 * ruta coincide exactamente. Sin esta excepcion, «Resumen» se queda encendido
 * estes donde estes y la barra deja de decir donde estas.
 */
export function esDestinoActivo(href: string, ruta: string): boolean {
  return href === '/panel' ? ruta === '/panel' : ruta === href || ruta.startsWith(`${href}/`);
}

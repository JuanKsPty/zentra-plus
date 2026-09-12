'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef } from 'react';

import { CanalDeAvisos } from '@/lib/realtime/socket';

/**
 * Refresca la pantalla cuando llega un aviso de los que le importan.
 *
 * `router.refresh()` reejecuta el componente de servidor, asi que no hay ni una
 * linea de cache de cliente que mantener. El rebote de 150 ms existe porque una
 * sola accion humana genera una rafaga —crear una comanda avisa de la comanda Y
 * de la mesa— y sin el serian varias peticiones por accion, multiplicadas por
 * cada pantalla abierta.
 */
export function Refrescador({ eventos }: { eventos: string[] }) {
  const router = useRouter();
  const pendiente = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const canal = new CanalDeAvisos();
    const interesan = new Set(eventos);

    const refrescar = () => {
      if (pendiente.current) clearTimeout(pendiente.current);
      pendiente.current = setTimeout(() => router.refresh(), 150);
    };

    const dejarDeEscuchar = canal.escuchar((aviso) => {
      if (interesan.has(aviso.tipo)) refrescar();
    });
    // Al volver la conexion hay que volver a pedir: el servidor difunde sin
    // bufer y lo emitido durante el corte se perdio.
    const dejarDeReconectar = canal.cuandoReconecte(refrescar);

    canal.conectar();

    return () => {
      dejarDeEscuchar();
      dejarDeReconectar();
      if (pendiente.current) clearTimeout(pendiente.current);
      canal.cerrar();
    };
  }, [eventos, router]);

  return null;
}

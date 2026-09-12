'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { CanalDeAvisos } from '@/lib/realtime/socket';

/**
 * Refresca la pantalla cuando llega un aviso de los que le importan, y DICE
 * cuando dejo de haber avisos.
 *
 * `router.refresh()` reejecuta el componente de servidor, asi que no hay ni una
 * linea de cache de cliente que mantener. El rebote de 150 ms existe porque una
 * sola accion humana genera una rafaga —crear una comanda avisa de la comanda Y
 * de la mesa— y sin el serian varias peticiones por accion, multiplicadas por
 * cada pantalla abierta.
 *
 * LO SEGUNDO NO ES UN EXTRA. Sin canal, esta pantalla no se rompe: se queda
 * quieta ensenando el mundo de hace diez minutos. En el tablero de cocina eso
 * se lee como «no hay comandas», que es exactamente lo contrario de lo que
 * pasa. Refrescar y avisar van juntos aqui porque comparten el mismo canal:
 * separarlos obligaria a abrir dos conexiones SSE por pantalla.
 */

/**
 * Cuanto se espera antes de acusar al canal de estar caido.
 *
 * `EventSource` reconecta solo con su propio retroceso, y un bache de dos
 * segundos en el WiFi del local es normal. Sin esta gracia, el aviso
 * parpadearia en cada bache y en un mes nadie lo miraria — que es la forma
 * ordinaria de que un aviso deje de servir para nada.
 */
const GRACIA_MS = 5000;

export function Refrescador({ eventos }: { eventos: string[] }) {
  const router = useRouter();
  const pendiente = useRef<ReturnType<typeof setTimeout> | null>(null);
  const espera = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sinCanal, setSinCanal] = useState(false);

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

    // El canal avisa YA del estado al suscribirse, y al montar ese estado es
    // «todavia no conectado»: la cuenta atras arranca aqui. Asi la pantalla que
    // NUNCA llega a conectar —la API caida desde el principio— tambien lo dice,
    // que es justo el caso en el que el tablero se queda mas viejo.
    const dejarDeObservar = canal.observarConexion((conectado) => {
      if (espera.current) clearTimeout(espera.current);
      if (conectado) setSinCanal(false);
      else espera.current = setTimeout(() => setSinCanal(true), GRACIA_MS);
    });

    canal.conectar();

    return () => {
      dejarDeEscuchar();
      dejarDeReconectar();
      dejarDeObservar();
      if (pendiente.current) clearTimeout(pendiente.current);
      if (espera.current) clearTimeout(espera.current);
      canal.cerrar();
    };
  }, [eventos, router]);

  if (!sinCanal) return null;

  return (
    // `output` trae `role="status"` de serie: es una condicion que persiste, no
    // una interrupcion, asi que un lector de pantalla lo anuncia sin cortar lo
    // que estuviera leyendo.
    <output
      aria-live="polite"
      className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-xl border border-warning/25 bg-warning/12 px-4 py-3"
    >
      <span className="text-sm font-medium text-warning">Sin avisos en vivo</span>
      <span className="text-sm text-muted-foreground">
        Esta pantalla ya no se actualiza sola: lo que ves puede estar viejo. Se reconecta sola
        en cuanto vuelva la red.
      </span>
    </output>
  );
}

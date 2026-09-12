/**
 * El canal de avisos, por Server-Sent Events.
 *
 * POR QUE SSE Y NO UN WEBSOCKET. El navegador habla siempre con su propio
 * origen y el servidor de Next reenvia `/api` a la API — y ese reenvio NO PUEDE
 * atravesar el «upgrade» de un WebSocket. Con Dockerfiles separados y sin un
 * proxy de borde delante, el socket sencillamente no llega. Se descubrio
 * probandolo de punta a punta.
 *
 * Y encaja mejor con lo que esto es: el evento es una SENAL —«mira otra vez»—,
 * no un canal de datos, asi que no hace falta que el cliente pueda hablar de
 * vuelta. De paso, `EventSource` reconecta solo y manda la cookie de sesion
 * como cualquier peticion del mismo origen.
 *
 * Lo que SI hay que escribir: distinguir la PRIMERA conexion de una
 * RECONEXION. Al volver hay que pedir los datos otra vez, porque el servidor
 * difunde sin bufer y lo emitido durante el corte se perdio; pero refrescar en
 * la primera conexion seria una peticion tirada encima del render que acaba de
 * llegar.
 */

export interface Aviso {
  tipo: string;
  branchId: string;
  emitidoEn: string;
  payload: Record<string, unknown>;
}

type Escucha = (aviso: Aviso) => void;

export class CanalDeAvisos {
  private fuente: EventSource | null = null;
  private escuchas = new Set<Escucha>();
  private alReconectar = new Set<() => void>();
  private yaConecto = false;

  conectar(): void {
    if (this.fuente) return;

    const fuente = new EventSource('/api/events');
    this.fuente = fuente;

    fuente.onopen = () => {
      if (this.yaConecto) {
        // Solo al VOLVER. La primera conexion no dispara nada.
        for (const accion of this.alReconectar) accion();
      }
      this.yaConecto = true;
    };

    fuente.onmessage = (evento) => {
      const datos = JSON.parse(evento.data);
      if (datos.tipo === 'conectado') return;
      for (const escucha of this.escuchas) escucha(datos as Aviso);
    };

    // `EventSource` reintenta solo tras un error, con su propio retroceso. No
    // se cierra aqui: cerrarlo seria renunciar a la reconexion automatica, que
    // es justo lo que se estaba aprovechando.
  }

  cerrar(): void {
    this.fuente?.close();
    this.fuente = null;
  }

  escuchar(escucha: Escucha): () => void {
    this.escuchas.add(escucha);
    return () => this.escuchas.delete(escucha);
  }

  cuandoReconecte(accion: () => void): () => void {
    this.alReconectar.add(accion);
    return () => this.alReconectar.delete(accion);
  }
}

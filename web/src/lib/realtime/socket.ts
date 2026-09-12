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
 *
 * Y lo segundo: DECIR que se esta sin canal. `EventSource` reintenta solo y en
 * silencio, asi que una pantalla que perdio el SSE no se rompe — se congela. Un
 * tablero de cocina congelado ensena el mundo de hace diez minutos y se lee
 * como «no hay trabajo», que es la lectura contraria a la verdadera. Por eso el
 * estado de la conexion es algo que el canal PUBLICA, no algo que se deduce.
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
  private observadores = new Set<(conectado: boolean) => void>();
  private yaConecto = false;
  private conectado = false;

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
      this.marcar(true);
    };

    // `onerror` salta tanto cuando la conexion se cae como cuando un intento de
    // reconexion falla. No se distingue a proposito: para quien mira la
    // pantalla, las dos cosas son lo mismo — ahora mismo no llegan avisos.
    fuente.onerror = () => {
      this.marcar(false);
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
    // Cerrado a proposito NO es lo mismo que caido: no se avisa a nadie. Quien
    // cierra es la propia pantalla al desmontarse, y ya no hay nada que
    // advertir.
    this.conectado = false;
  }

  escuchar(escucha: Escucha): () => void {
    this.escuchas.add(escucha);
    return () => this.escuchas.delete(escucha);
  }

  cuandoReconecte(accion: () => void): () => void {
    this.alReconectar.add(accion);
    return () => this.alReconectar.delete(accion);
  }

  /**
   * Avisa de si hay canal o no, y avisa YA del estado actual al suscribirse.
   *
   * Lo de avisar al suscribirse no es comodidad: `conectar()` puede haber
   * pasado antes de que la pantalla se suscriba, y sin el estado inicial la
   * pantalla se quedaria esperando un cambio que ya ocurrio.
   */
  observarConexion(observador: (conectado: boolean) => void): () => void {
    this.observadores.add(observador);
    observador(this.conectado);
    return () => this.observadores.delete(observador);
  }

  private marcar(conectado: boolean): void {
    if (this.conectado === conectado) return;
    this.conectado = conectado;
    for (const observador of this.observadores) observador(conectado);
  }
}

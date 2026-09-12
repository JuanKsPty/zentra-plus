import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CanalDeAvisos } from './socket';

/**
 * Un `EventSource` de mentira.
 *
 * El de verdad reconecta solo, con su propio retroceso y sin decir nada: no hay
 * forma de provocar un corte desde fuera ni de esperar a que vuelva. Lo que se
 * prueba aqui no es el transporte —eso es el navegador— sino las dos decisiones
 * que este proyecto escribio encima: que la PRIMERA conexion no refresca y que
 * un corte se DICE.
 */
class FuenteFalsa {
  static ultima: FuenteFalsa | null = null;

  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  cerrada = false;

  constructor(readonly url: string) {
    FuenteFalsa.ultima = this;
  }

  close() {
    this.cerrada = true;
  }

  abrir() {
    this.onopen?.();
  }

  caer() {
    this.onerror?.();
  }

  emitir(datos: unknown) {
    this.onmessage?.({ data: JSON.stringify(datos) });
  }
}

beforeEach(() => {
  FuenteFalsa.ultima = null;
  vi.stubGlobal('EventSource', FuenteFalsa);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function abrirCanal() {
  const canal = new CanalDeAvisos();
  canal.conectar();
  const fuente = FuenteFalsa.ultima!;
  return { canal, fuente };
}

describe('el canal de avisos', () => {
  it('la primera conexion no refresca; la reconexion si', () => {
    // Refrescar en la primera conexion seria una peticion tirada encima del
    // render que acaba de llegar. Al VOLVER si hace falta: el servidor difunde
    // sin bufer y lo emitido durante el corte se perdio.
    const { canal, fuente } = abrirCanal();
    let vueltas = 0;
    canal.cuandoReconecte(() => vueltas++);

    fuente.abrir();
    expect(vueltas).toBe(0);

    fuente.caer();
    fuente.abrir();
    expect(vueltas).toBe(1);
  });

  it('un corte se dice, y volver lo desdice', () => {
    // Este es el fallo sin sintoma: sin canal la pantalla no se rompe, se
    // congela. Un tablero de cocina congelado se lee como «no hay trabajo».
    const { canal, fuente } = abrirCanal();
    const estados: boolean[] = [];
    canal.observarConexion((conectado) => estados.push(conectado));

    // Al suscribirse ya dice como esta: `conectar()` puede haber pasado antes.
    expect(estados).toEqual([false]);

    fuente.abrir();
    fuente.caer();
    fuente.abrir();

    expect(estados).toEqual([false, true, false, true]);
  });

  it('no repite el mismo estado dos veces seguidas', () => {
    // `onerror` salta en cada intento fallido de reconexion, y cada intento
    // haria parpadear el aviso si el canal lo propagara tal cual.
    const { canal, fuente } = abrirCanal();
    fuente.abrir();

    const estados: boolean[] = [];
    canal.observarConexion((conectado) => estados.push(conectado));

    fuente.caer();
    fuente.caer();
    fuente.caer();

    expect(estados).toEqual([true, false]);
  });

  it('dejar de observar deja de recibir', () => {
    const { canal, fuente } = abrirCanal();
    const estados: boolean[] = [];
    const dejar = canal.observarConexion((conectado) => estados.push(conectado));

    dejar();
    fuente.abrir();

    expect(estados).toEqual([false]);
  });

  it('el saludo del servidor no llega a las pantallas', () => {
    // `conectado` es el «hola» del SSE, no un aviso de dominio. Si pasara, cada
    // reconexion se contaria como un cambio y el salon se repintaria por nada.
    const { canal, fuente } = abrirCanal();
    const recibidos: string[] = [];
    canal.escuchar((aviso) => recibidos.push(aviso.tipo));

    fuente.emitir({ tipo: 'conectado' });
    fuente.emitir({ tipo: 'order.created', branchId: 'b1', emitidoEn: 'x', payload: {} });

    expect(recibidos).toEqual(['order.created']);
  });

  it('cerrar a proposito no es caerse: no avisa a nadie', () => {
    // Quien cierra es la pantalla al desmontarse. Un aviso de «sin conexion»
    // sobre una pantalla que ya no existe no lo lee nadie, y el estado que deja
    // no puede ser «conectado».
    const { canal, fuente } = abrirCanal();
    fuente.abrir();

    const estados: boolean[] = [];
    canal.cerrar();
    canal.observarConexion((conectado) => estados.push(conectado));

    expect(fuente.cerrada).toBe(true);
    expect(estados).toEqual([false]);
  });

  it('conectar dos veces no abre dos conexiones', () => {
    // Cada pantalla abierta es una conexion SSE viva contra la API. Duplicarla
    // por un render de mas se paga en el servidor, no aqui.
    const { canal, fuente } = abrirCanal();
    canal.conectar();

    expect(FuenteFalsa.ultima).toBe(fuente);
    expect(fuente.url).toBe('/api/events');
  });
});

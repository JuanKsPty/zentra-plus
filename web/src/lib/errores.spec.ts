import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, NetworkError } from '@/services/http';

import { describirFallo, esFalloDeApi, reportar } from './errores';

// Sonner pinta en el DOM y aqui no hay DOM. Lo que se comprueba no es el aviso
// flotante —eso es sonner— sino QUE se le pide que diga.
const avisos: { mensaje: string; detalle?: string }[] = [];

vi.mock('sonner', () => ({
  toast: {
    error: (mensaje: string, opciones?: { description?: string }) => {
      avisos.push({ mensaje, detalle: opciones?.description });
    },
  },
}));

beforeEach(() => {
  avisos.length = 0;
});

describe('como se le cuenta un fallo a una persona', () => {
  it('«no hay red» y «el servidor dijo que no» no se cuentan igual', () => {
    // Llevan a acciones distintas: lo primero se arregla mirando el router del
    // local y lo segundo no. Si las dos salen como «Error», el encargado no
    // sabe a quien llamar — que es exactamente el fallo que esto evita.
    const sinRed = describirFallo(new NetworkError());
    const deLaApi = describirFallo(new ApiError(409, 'La mesa ya tiene una cuenta abierta.'));

    expect(sinRed?.clase).toBe('sin-red');
    expect(deLaApi?.clase).toBe('api');
    expect(sinRed?.mensaje).not.toBe(deLaApi?.mensaje);
    // La red tiene una accion concreta que ofrecer; el 409 no.
    expect(sinRed?.pista).toContain('red del local');
  });

  it('el mensaje de la API se ensena tal cual, sin envolverlo', () => {
    // Los mensajes de la API son interfaz y vienen en espanol. Sustituirlos por
    // uno generico tira justo la informacion que hace accionable el aviso.
    const fallo = describirFallo(new ApiError(409, 'El turno ya esta cerrado.'));
    expect(fallo?.mensaje).toBe('El turno ya esta cerrado.');
  });

  it('lo que no es de la API ni de la red no se describe: no se inventa un texto', () => {
    expect(describirFallo(new TypeError('x.map is not a function'))).toBeNull();
    expect(describirFallo('cadena suelta')).toBeNull();
    expect(describirFallo(undefined)).toBeNull();

    expect(esFalloDeApi(new NetworkError())).toBe(true);
    expect(esFalloDeApi(new ApiError(500, 'boom'))).toBe(true);
    expect(esFalloDeApi(new TypeError('boom'))).toBe(false);
  });

  it('un TypeError se relanza en vez de disfrazarse de error del servidor', () => {
    // Sin esto, un bug del navegador manda a alguien a revisar el router y el
    // fallo real no aparece ni en la consola.
    const bug = new TypeError('comandas.map is not a function');
    expect(() => reportar(bug)).toThrow(bug);
    expect(avisos).toEqual([]);
  });

  it('el identificador de la peticion queda a la vista cuando lo hay', () => {
    // En produccion es lo UNICO que enlaza lo que vio el operario con la linea
    // del log del servidor. Si no se ensena, no se puede pedir por telefono.
    reportar(new ApiError(500, 'Algo fallo.', 'error', {}, 'req-9f3c'));

    expect(avisos).toHaveLength(1);
    expect(avisos[0]?.mensaje).toBe('Algo fallo.');
    expect(avisos[0]?.detalle).toContain('req-9f3c');
  });

  it('sin identificador no se inventa una referencia vacia', () => {
    reportar(new ApiError(409, 'El turno ya esta cerrado.'));

    expect(avisos[0]?.detalle ?? '').not.toContain('Referencia');
  });

  it('el contexto dice QUE accion se quedo sin hacer', () => {
    // El mensaje de la API dice que fallo, no que se dejo de hacer. En una
    // tableta el aviso puede llegar dos pantallas despues de la pulsacion.
    reportar(new NetworkError(), 'No se pudo cobrar la cuenta.');

    expect(avisos[0]?.mensaje).toBe('No hay conexion con el servidor.');
    expect(avisos[0]?.detalle).toBe('No se pudo cobrar la cuenta. Comprueba la red del local.');
  });
});

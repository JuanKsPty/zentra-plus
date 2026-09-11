import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, NetworkError, apiFetch } from './http';

const respuesta = (status: number, cuerpo: unknown = {}) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'content-type': 'application/json' },
  });

const sobreDeError = (code: string, message: string, details: unknown[] = []) => ({
  error: { code, message, details, request_id: 'r-1' },
});

let llamadas: string[] = [];

beforeEach(() => {
  llamadas = [];
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function simular(secuencia: Response[]) {
  let indice = 0;
  vi.stubGlobal('fetch', (url: string) => {
    llamadas.push(new URL(url, 'http://x').pathname);
    return Promise.resolve(secuencia[Math.min(indice++, secuencia.length - 1)]!);
  });
}

describe('el cliente de la API', () => {
  it('un 401 dispara UN refresco y reenvia la misma peticion', () => {
    // La razon de que sea uno y no varios: reintentar mas no arregla nada y, en
    // cuanto haya cobros, multiplica el dano.
    simular([respuesta(401, sobreDeError('sesion_expirada', 'expiro')), respuesta(200), respuesta(200, { ok: true })]);

    return apiFetch('/orders').then((datos) => {
      expect(datos).toEqual({ ok: true });
      expect(llamadas).toEqual(['/api/orders', '/api/auth/refresh', '/api/orders']);
    });
  });

  it('un PIN mal tecleado NO intenta refrescar', async () => {
    // Sin esta excepcion, un dedo torpe dispararia un refresco, fallaria, y
    // echaria al operario del sistema: «llama al encargado» por un digito.
    simular([respuesta(401, sobreDeError('pin_invalido', 'PIN incorrecto.'))]);

    await expect(apiFetch('/auth/pin', { method: 'POST', body: {} })).rejects.toBeInstanceOf(
      ApiError,
    );
    expect(llamadas).toEqual(['/api/auth/pin']);
  });

  it('aplana los errores por campo que manda la API', async () => {
    simular([
      respuesta(
        422,
        sobreDeError('datos_invalidos', 'Revisa los datos', [
          { field: 'email', message: 'Hace falta este dato.' },
          { field: null, message: 'Algo general' },
        ]),
      ),
    ]);

    const error = (await apiFetch('/x').catch((e) => e)) as ApiError;

    expect(error.code).toBe('datos_invalidos');
    expect(error.fieldErrors).toEqual({ email: 'Hace falta este dato.' });
    expect(error.requestId).toBe('r-1');
  });

  it('distingue «no hay red» de «el servidor contesto que no»', async () => {
    vi.stubGlobal('fetch', () => Promise.reject(new TypeError('Failed to fetch')));

    await expect(apiFetch('/x')).rejects.toBeInstanceOf(NetworkError);
  });

  it('un cuerpo que no es JSON no pierde el codigo de estado', async () => {
    // Pasa con un 502 que pone un proxy y no la aplicacion.
    vi.stubGlobal('fetch', () => Promise.resolve(new Response('<html>502</html>', { status: 502 })));

    const error = (await apiFetch('/x').catch((e) => e)) as ApiError;

    expect(error.status).toBe(502);
  });
});

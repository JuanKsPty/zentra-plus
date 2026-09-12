import 'server-only';

import { cookies } from 'next/headers';

import { API_BASE_URL } from '@/lib/env';
import { ApiError, NetworkError } from '@/services/http';

/**
 * El cliente del SERVIDOR. Para componentes de servidor, que son los que leen.
 *
 * Existe aparte del de navegador por una razon concreta y no por simetria:
 * `credentials: 'include'` NO HACE NADA en el servidor. Ahi no hay tarro de
 * galletas — la cookie la tiene el navegador, y si no se reenvia a mano la API
 * responde 401 a todo. El sintoma es cruel: la misma peticion funciona desde la
 * pestana de red del navegador y falla al renderizar la pagina.
 *
 * `import 'server-only'` rompe el build si alguien lo importa desde un
 * componente de cliente, que es mejor que descubrirlo con `cookies()`
 * explotando en tiempo de ejecucion.
 *
 * Aqui NO hay reintento con refresco: si el token caduco, quien lo renueva es
 * el navegador en su siguiente peticion. Intentarlo desde el servidor exigiria
 * reemitir la cookie durante el render, que Next no permite.
 */
export async function apiFetchServidor<T>(path: string, opciones: RequestInit = {}): Promise<T> {
  const galletas = await cookies();

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_BASE_URL}/api${path}`, {
      ...opciones,
      headers: {
        ...opciones.headers,
        cookie: galletas.toString(),
      },
      // Nunca cacheado. Ademas de que estos datos cambian cada minuto, una
      // revalidacion por etiqueta sin la sucursal en la clave mezclaria datos de
      // dos sedes — el fallo mas caro posible en este producto.
      cache: 'no-store',
    });
  } catch (causa) {
    throw new NetworkError(undefined, { cause: causa });
  }

  if (!respuesta.ok) {
    let mensaje = `La peticion fallo con un ${respuesta.status}`;
    let codigo = 'error';
    // El identificador de la peticion llega hasta la pantalla A PROPOSITO: lo
    // que falla al renderizar no deja rastro en la pestana de red del
    // navegador, asi que esa referencia es lo unico que enlaza lo que vio el
    // operario con la linea del log de la API.
    let identificador: string | null = null;
    try {
      const cuerpo = await respuesta.json();
      if (cuerpo?.error?.message) {
        mensaje = cuerpo.error.message;
        codigo = cuerpo.error.code ?? codigo;
      }
      identificador = cuerpo?.error?.request_id ?? null;
    } catch {
      // Un cuerpo que no es JSON no es motivo para perder el codigo de estado.
    }
    throw new ApiError(respuesta.status, mensaje, codigo, {}, identificador);
  }

  if (respuesta.status === 204) return undefined as T;
  const texto = await respuesta.text();
  return (texto ? JSON.parse(texto) : undefined) as T;
}

import { API_BASE_URL } from '@/lib/env';

/** El servidor contesto, y contesto que no. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * No se pudo hablar con el servidor: la API esta apagada, el WiFi del local
 * se cayo o el DNS no resuelve.
 *
 * Se distingue de ApiError a proposito. `fetch` solo rechaza cuando la
 * peticion no llega a completarse; cualquier respuesta, incluido un 500,
 * resuelve. Ese es el unico punto donde se pueden separar, y separarlas
 * importa: lo primero se arregla mirando el router del local y lo segundo no.
 * Si las dos salen como «Error», el encargado no sabe a quien llamar.
 */
export class NetworkError extends Error {
  constructor(message = 'No hay conexion con el servidor', options?: ErrorOptions) {
    super(message, options);
    this.name = 'NetworkError';
  }
}

interface Opciones extends Omit<RequestInit, 'body'> {
  body?: unknown;
}

/**
 * La unica funcion que habla con la API.
 *
 * Pone la base, manda la cookie de sesion y normaliza los errores. Ningun
 * componente debe llamar a `fetch` por su cuenta.
 */
export async function apiFetch<T>(path: string, opciones: Opciones = {}): Promise<T> {
  const { body, headers, ...resto } = opciones;

  let respuesta: Response;
  try {
    respuesta = await fetch(`${API_BASE_URL}/api${path}`, {
      ...resto,
      credentials: 'include',
      cache: 'no-store',
      headers: {
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...headers,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (causa) {
    throw new NetworkError(undefined, { cause: causa });
  }

  if (!respuesta.ok) {
    throw new ApiError(respuesta.status, await mensajeDeError(respuesta));
  }

  // 204 y cuerpos vacios: devolver undefined es mas util que reventar en .json()
  if (respuesta.status === 204) return undefined as T;
  const texto = await respuesta.text();
  return (texto ? JSON.parse(texto) : undefined) as T;
}

async function mensajeDeError(respuesta: Response): Promise<string> {
  try {
    const cuerpo = await respuesta.json();
    // El sobre de error de la API: { error: { code, message } }
    if (typeof cuerpo?.error?.message === 'string') return cuerpo.error.message;
  } catch {
    // Un cuerpo que no es JSON no es motivo para perder el codigo de estado.
  }
  return `La peticion fallo con un ${respuesta.status}`;
}

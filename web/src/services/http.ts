import { API_BASE_URL } from '@/lib/env';
import type { ErrorDto } from '@/types/api';

/** El servidor contesto, y contesto que no. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
    /** Codigo estable de la API. Es lo que se compara, nunca el mensaje. */
    readonly code: string = 'error',
    /**
     * Problemas por campo, ya aplanados. Se vuelcan en el formulario con
     * `setError`; sin aplanarlos aqui, cada formulario tendria que recorrer la
     * lista de la API y decidir por su cuenta que hacer con ella.
     */
    readonly fieldErrors: Record<string, string> = {},
    /** Enlaza este error con la linea del log de la API. */
    readonly requestId: string | null = null,
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
    throw await errorDeRespuesta(respuesta);
  }

  // 204 y cuerpos vacios: devolver undefined es mas util que reventar en .json()
  if (respuesta.status === 204) return undefined as T;
  const texto = await respuesta.text();
  return (texto ? JSON.parse(texto) : undefined) as T;
}

async function errorDeRespuesta(respuesta: Response): Promise<ApiError> {
  let cuerpo: ErrorDto | undefined;
  try {
    cuerpo = (await respuesta.json()) as ErrorDto;
  } catch {
    // Un cuerpo que no es JSON no es motivo para perder el codigo de estado.
    // Pasa, por ejemplo, con un 502 que pone el proxy y no la aplicacion.
  }

  const error = cuerpo?.error;
  if (!error) {
    return new ApiError(respuesta.status, `La peticion fallo con un ${respuesta.status}`);
  }

  const fieldErrors: Record<string, string> = {};
  for (const detalle of error.details ?? []) {
    // Los detalles sin campo (una regla que mira varios a la vez) no van al
    // formulario: ya estan dichos en el mensaje general.
    if (detalle.field) fieldErrors[detalle.field] = detalle.message;
  }

  return new ApiError(respuesta.status, error.message, error.code, fieldErrors, error.request_id);
}

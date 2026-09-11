import { API_BASE_URL } from '@/lib/env';
import type { ErrorDto, Pagina, PaginaDto } from '@/types/api';

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
 * Donde volver a entrar cuando la sesion se acaba de verdad.
 *
 * La cookie de sesion es httpOnly, asi que el navegador NO puede saber si se
 * entro por correo o por PIN. Se guarda una pista —solo eso, ningun secreto—
 * al entrar, porque mandar a un mesero al formulario de correo es mandarlo a
 * una pantalla donde no tiene credenciales que poner.
 */
const CLAVE_PUERTA = 'zentra:puerta';

export function recordarPuerta(puerta: 'email' | 'pin'): void {
  try {
    localStorage.setItem(CLAVE_PUERTA, puerta);
  } catch {
    // Ventana privada o almacenamiento bloqueado: se pierde la pista y se cae
    // al formulario de correo. Es peor que acertar, y mucho mejor que reventar.
  }
}

function puertaRecordada(): string {
  try {
    return localStorage.getItem(CLAVE_PUERTA) === 'pin' ? '/acceso/pin' : '/acceso';
  } catch {
    return '/acceso';
  }
}

/**
 * Rutas donde un 401 significa «esas credenciales no valen», no «tu sesion
 * caduco».
 *
 * Sin esta excepcion, teclear mal el PIN dispararia un intento de refresco y,
 * al fallar, echaria al operario del sistema. Un dedo torpe se convertiria en
 * «llama al encargado».
 */
const COMPROBACION_DE_CREDENCIALES = ['/auth/login', '/auth/pin', '/auth/refresh'];

/**
 * La unica funcion que habla con la API.
 *
 * Pone la base, manda la cookie de sesion y normaliza los errores. Ningun
 * componente debe llamar a `fetch` por su cuenta.
 */
export async function apiFetch<T>(path: string, opciones: Opciones = {}): Promise<T> {
  let respuesta = await enviar(path, opciones);

  // UN solo reintento, y solo ante un 401 de sesion caducada.
  //
  // Se reenvia la MISMA peticion, con el mismo cuerpo: cuando haya claves de
  // reenvio, eso es lo que garantiza que un reintento no cobre ni pida dos
  // veces. Reintentar mas de una vez no arregla nada y multiplica el dano.
  if (respuesta.status === 401 && !COMPROBACION_DE_CREDENCIALES.includes(path)) {
    const renovada = await enviar('/auth/refresh', { method: 'POST' });
    if (renovada.ok) {
      respuesta = await enviar(path, opciones);
    } else if (typeof window !== 'undefined') {
      // La sesion se acabo de verdad. Se va a la puerta por la que entro, no a
      // la de siempre.
      window.location.href = puertaRecordada();
      throw new ApiError(401, 'La sesion expiro. Vuelve a entrar.', 'sesion_expirada');
    }
  }

  if (!respuesta.ok) {
    throw await errorDeRespuesta(respuesta);
  }

  // 204 y cuerpos vacios: devolver undefined es mas util que reventar en .json()
  if (respuesta.status === 204) return undefined as T;
  const texto = await respuesta.text();
  return (texto ? JSON.parse(texto) : undefined) as T;
}

async function enviar(path: string, opciones: Opciones): Promise<Response> {
  const { body, headers, ...resto } = opciones;
  try {
    return await fetch(`${API_BASE_URL}/api${path}`, {
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

/**
 * Convierte una pagina de la API al dominio, aplicando el mapeador a cada
 * elemento. Sin esto, cada servicio repetiria las cinco lineas de la envoltura
 * y alguno acabaria olvidandose de `hasMore`.
 */
export function aPagina<D, T>(dto: PaginaDto<D>, aDominio: (d: D) => T): Pagina<T> {
  return {
    items: dto.items.map(aDominio),
    page: dto.page,
    size: dto.size,
    total: dto.total,
    hasMore: dto.has_more,
  };
}

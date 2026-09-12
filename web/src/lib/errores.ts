import { toast } from 'sonner';

import { ApiError, NetworkError } from '@/services/http';

/**
 * El UNICO sitio del web que decide como se le cuenta un fallo a una persona.
 *
 * Antes esto estaba copiado en cada componente: tres ramas identicas —sin red,
 * error de la API, y relanzar lo demas— repetidas en la caja, en el salon, en
 * la cocina y en el panel. Copiado nueve veces no es un patron, es nueve sitios
 * donde el mensaje puede divergir; y divergio: unos ponian el punto final y
 * otros no, y NINGUNO ensenaba el identificador de la peticion.
 *
 * Aqui NO hay telemetria ni se envia nada a ningun sitio: este proyecto no tiene
 * backend de errores. «Reportar» es contarselo a quien esta delante de la
 * pantalla, que es el unico destinatario que existe.
 *
 * Las tres decisiones que se toman aqui, y solo aqui:
 *
 *  1. `NetworkError` y `ApiError` NO se dicen igual. Lo primero se arregla
 *     mirando el router del local; lo segundo no. Si las dos salen como
 *     «Error», el encargado no sabe a quien llamar.
 *  2. El `request_id` se ENSENA cuando lo hay. En produccion el mensaje del
 *     servidor puede ser generico, y esa referencia es lo unico que enlaza lo
 *     que vio el operario con la linea del log. Pedirsela por telefono vale mas
 *     que cualquier captura de pantalla.
 *  3. Lo que no es ninguna de las dos se RELANZA. Un `TypeError` de un `.map`
 *     sobre undefined disfrazado de «error del servidor» manda a alguien a
 *     revisar la red por un bug del navegador, y el fallo real no aparece ni en
 *     la consola.
 */

/** Lo que se le cuenta a una persona sobre un fallo, ya decidido. */
export interface FalloContado {
  /** `sin-red` se arregla mirando el router del local; `api` no. */
  clase: 'sin-red' | 'api';
  /** Titulo corto, para el aviso de pantalla completa. */
  titulo: string;
  /** Que ha pasado, en una frase. Es el texto del toast. */
  mensaje: string;
  /** Que hacer, cuando hay algo que hacer. */
  pista: string | null;
  /** El `request_id` de la API: la linea del log del servidor. */
  referencia: string | null;
}

/**
 * Traduce un error a lo que se le ensena a una persona.
 *
 * Devuelve `null` —y no un texto de relleno— cuando el error NO es uno de los
 * dos que sabemos contar. Quien llama decide: las pantallas relanzan (y lo
 * recoge `error.tsx`), `reportar` tambien.
 */
export function describirFallo(error: unknown): FalloContado | null {
  if (error instanceof NetworkError) {
    return {
      clase: 'sin-red',
      titulo: 'Sin conexion',
      mensaje: 'No hay conexion con el servidor.',
      pista: 'Comprueba la red del local.',
      referencia: null,
    };
  }

  if (error instanceof ApiError) {
    return {
      clase: 'api',
      titulo: 'El servidor no respondio',
      // El mensaje de la API es interfaz y viene en espanol: se ensena tal cual.
      mensaje: error.message,
      pista: null,
      referencia: error.requestId,
    };
  }

  return null;
}

/** Un fallo del que sabemos hablar. Lo demas sube hasta `error.tsx`. */
export function esFalloDeApi(error: unknown): boolean {
  return describirFallo(error) !== null;
}

/**
 * Cuenta un fallo a quien esta delante, en un aviso flotante.
 *
 * `contexto` es lo que la persona estaba intentando hacer —«No se pudo cobrar
 * la cuenta»—, porque el mensaje de la API dice que fallo pero no QUE accion se
 * quedo sin hacer, y en una tableta el toast puede llegar dos pantallas despues.
 *
 * RELANZA lo que no sabe contar. No es un descuido: es la unica forma de que un
 * bug del navegador siga pareciendo un bug del navegador.
 */
export function reportar(error: unknown, contexto?: string): void {
  const fallo = describirFallo(error);
  if (!fallo) throw error;

  const detalle = [
    contexto,
    fallo.pista,
    fallo.referencia ? `Referencia: ${fallo.referencia}` : null,
  ]
    .filter((parte): parte is string => Boolean(parte))
    .join(' ');

  toast.error(fallo.mensaje, detalle ? { description: detalle } : undefined);
}

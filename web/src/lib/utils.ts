import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Une clases y resuelve conflictos de Tailwind.
 *
 * Ojo con lo que `tailwind-merge` NO considera conflicto: `h-12` y `sm:h-8` son
 * modificadores distintos, asi que conviven. Por eso las primitivas escriben
 * siempre `valor-escritorio max-sm:valor-movil` y nunca al reves — con la forma
 * ascendente, un `className="h-12"` de quien llama dejaria `h-12 sm:h-8` y el
 * control encogeria en escritorio sin que nadie lo note.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

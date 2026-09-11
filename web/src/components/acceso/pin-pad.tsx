'use client';

import { DeleteIcon } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { ApiError, NetworkError } from '@/services/http';
import { entrarConPin } from '@/services/authService';

const LARGO = 4;
const TECLAS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'];

/**
 * El teclado del PIN.
 *
 * Escrito a mano y no con un campo de codigo: aqui lo que importa son teclas de
 * 56 px que se pulsan de pie y sin mirar, no un `<input>` que abre el teclado
 * del sistema encima de la pantalla.
 */
export function TecladoDePin({ empleadoId, nombre }: { empleadoId: string; nombre: string }) {
  const router = useRouter();
  const [pin, setPin] = useState('');
  const [enviando, setEnviando] = useState(false);

  async function intentar(valor: string) {
    setEnviando(true);
    try {
      await entrarConPin(empleadoId, valor);
      router.push('/');
      router.refresh();
    } catch (error) {
      setPin('');
      if (error instanceof NetworkError) {
        toast.error('No hay conexion con el servidor.');
      } else if (error instanceof ApiError) {
        toast.error(error.message);
      } else {
        throw error;
      }
      setEnviando(false);
    }
  }

  function pulsar(digito: string) {
    if (enviando || pin.length >= LARGO) return;
    const siguiente = pin + digito;
    setPin(siguiente);
    if (siguiente.length === LARGO) void intentar(siguiente);
  }

  return (
    <div className="w-full max-w-xs space-y-6">
      <p className="text-center text-sm text-muted-foreground">
        Hola, <span className="font-medium text-foreground">{nombre}</span>
      </p>

      <div className="flex justify-center gap-3" aria-label={`PIN de ${pin.length} de ${LARGO}`}>
        {Array.from({ length: LARGO }, (_, indice) => (
          <span
            key={indice}
            className={
              indice < pin.length
                ? 'size-3.5 rounded-full bg-primary'
                : 'size-3.5 rounded-full border border-border'
            }
          />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {TECLAS.map((tecla) => (
          <Button
            key={tecla}
            variant="outline"
            size="key"
            className="font-mono tabular-nums"
            disabled={enviando}
            onClick={() => pulsar(tecla)}
          >
            {tecla}
          </Button>
        ))}
        <span />
        <Button
          variant="outline"
          size="key"
          className="font-mono tabular-nums"
          disabled={enviando}
          onClick={() => pulsar('0')}
        >
          0
        </Button>
        <Button
          variant="ghost"
          size="key"
          aria-label="Borrar"
          disabled={enviando || pin.length === 0}
          onClick={() => setPin((actual) => actual.slice(0, -1))}
        >
          <DeleteIcon />
        </Button>
      </div>

      {enviando && (
        <p className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
          <Spinner /> Comprobando
        </p>
      )}
    </div>
  );
}

'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Input } from '@/components/ui/input';
import type { Categoria } from '@/services/catalogService';

/**
 * Busqueda y filtro, con el estado EN LA URL.
 *
 * Que viva en la URL y no en un `useState` es lo que hace que un filtro se pueda
 * compartir por mensaje, recargar sin perderlo y volver atras con el navegador.
 */
export function FiltroDeCarta({ categorias }: { categorias: Categoria[] }) {
  const router = useRouter();
  const parametros = useSearchParams();
  const [texto, setTexto] = useState(parametros.get('q') ?? '');

  // Rebote de 300 ms. Sin el, escribir «hamburguesa» dispara once peticiones y
  // la respuesta de la cuarta puede pintar encima de la undecima.
  useEffect(() => {
    const espera = setTimeout(() => {
      const siguientes = new URLSearchParams(parametros.toString());
      if (texto.trim()) siguientes.set('q', texto.trim());
      else siguientes.delete('q');
      router.replace(`/panel/catalogo?${siguientes}`);
    }, 300);
    return () => clearTimeout(espera);
    // `parametros` cambia de identidad en cada render; incluirlo relanzaria el
    // efecto en bucle.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [texto]);

  function filtrarPorCategoria(id: string) {
    const siguientes = new URLSearchParams(parametros.toString());
    if (id) siguientes.set('categoria', id);
    else siguientes.delete('categoria');
    router.replace(`/panel/catalogo?${siguientes}`);
  }

  return (
    <div className="flex flex-wrap gap-3">
      <Input
        value={texto}
        onChange={(evento) => setTexto(evento.target.value)}
        placeholder="Buscar en la carta"
        aria-label="Buscar en la carta"
        className="max-w-xs"
      />
      <select
        value={parametros.get('categoria') ?? ''}
        onChange={(evento) => filtrarPorCategoria(evento.target.value)}
        aria-label="Filtrar por seccion"
        className="h-8 max-sm:h-11 rounded-lg border border-input bg-transparent px-2.5 text-sm"
      >
        <option value="">Todas las secciones</option>
        {categorias.map((categoria) => (
          <option key={categoria.id} value={categoria.id}>
            {categoria.nombre}
          </option>
        ))}
      </select>
    </div>
  );
}

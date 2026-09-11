import { Suspense } from 'react';

import { FormularioDeAcceso } from '@/components/acceso/login-form';

export const metadata = { title: 'Entrar · Zentra+' };

export default function Acceso() {
  return (
    // `useSearchParams` obliga a un limite de Suspense, o la pagina entera se
    // vuelve dinamica y deja de prerenderizarse.
    <Suspense>
      <FormularioDeAcceso />
    </Suspense>
  );
}

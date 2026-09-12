'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useForm } from 'react-hook-form';

import { Button } from '@/components/ui/button';
import { Field, FieldError, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';
import { reportar } from '@/lib/errores';
import { z } from '@/lib/validations/zod';
import { entrarConCorreo } from '@/services/authService';

const esquema = z.object({
  email: z.string().min(3, 'Escribe tu correo'),
  password: z.string().min(1, 'Escribe tu contrasena'),
});

type Valores = z.infer<typeof esquema>;

export function FormularioDeAcceso() {
  const router = useRouter();
  const parametros = useSearchParams();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Valores>({ resolver: zodResolver(esquema) });

  async function enviar(valores: Valores) {
    try {
      await entrarConCorreo(valores.email, valores.password);
    } catch (error) {
      // «No hay red» y «esas credenciales no valen» llevan a acciones
      // distintas: lo primero se arregla mirando el router del local. Quien lo
      // separa es `reportar`, en un solo sitio para todo el web.
      reportar(error, 'No se pudo entrar.');
      return;
    }

    // Solo se acepta una ruta relativa. Un destino absoluto convertiria esto en
    // un redirector abierto hacia cualquier sitio.
    const volver = parametros.get('volver');
    const destino = volver?.startsWith('/') && !volver.startsWith('//') ? volver : null;

    // Sin destino guardado se va a la raiz, que decide por rol. Calcularlo aqui
    // significaria tener una segunda copia de `destinoPara` con los permisos
    // que el cliente cree tener; la raiz lo resuelve con el token ya puesto.
    router.push(destino ?? '/');
    router.refresh();
  }

  return (
    <form
      onSubmit={handleSubmit(enviar)}
      className="w-full max-w-sm rounded-xl border border-border bg-card p-6"
    >
      <FieldGroup>
        <Field data-invalid={errors.email ? true : undefined}>
          <FieldLabel htmlFor="email">Correo</FieldLabel>
          <Input
            id="email"
            type="email"
            autoComplete="username"
            inputMode="email"
            aria-invalid={errors.email ? true : undefined}
            {...register('email')}
          />
          <FieldError errors={errors.email ? [errors.email] : undefined} />
        </Field>

        <Field data-invalid={errors.password ? true : undefined}>
          <FieldLabel htmlFor="password">Contrasena</FieldLabel>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            aria-invalid={errors.password ? true : undefined}
            {...register('password')}
          />
          <FieldError errors={errors.password ? [errors.password] : undefined} />
        </Field>

        <Button type="submit" size="touch" disabled={isSubmitting} className="w-full">
          {isSubmitting && <Spinner />}
          Entrar
        </Button>
      </FieldGroup>

      <p className="mt-5 text-center text-sm text-muted-foreground">
        ¿Trabajas en el salon?{' '}
        <Link href="/acceso/pin" className="text-primary underline-offset-4 hover:underline">
          Entra con tu PIN
        </Link>
      </p>
    </form>
  );
}

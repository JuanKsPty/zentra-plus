'use client';

/**
 * El ultimo recurso: un fallo en el layout raiz.
 *
 * Sin este archivo, Next pinta su `DefaultGlobalError`, que EMITE SU PROPIO
 * `<html>` y sustituye al layout entero — se van las fuentes, las variables del
 * tema y los avisos, y el operario ve una pantalla en ingles que no se parece
 * al sistema.
 *
 * Los estilos van EN LINEA a proposito: una causa perfectamente posible de
 * llegar aqui es que la hoja de estilos no haya cargado, y una pantalla de
 * error que depende de la hoja que fallo no sirve de nada. Por lo mismo el tema
 * se resuelve con `prefers-color-scheme` y no con la clase `.dark`, que en este
 * punto no esta puesta.
 */
export default function ErrorGlobal({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="es">
      <body
        style={{
          margin: 0,
          minHeight: '100dvh',
          display: 'grid',
          placeItems: 'center',
          padding: '2rem',
          textAlign: 'center',
          fontFamily: 'system-ui, sans-serif',
          colorScheme: 'light dark',
          background: 'Canvas',
          color: 'CanvasText',
        }}
      >
        <div style={{ maxWidth: '28rem' }}>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 600, margin: '0 0 0.5rem' }}>
            Zentra+ no pudo arrancar
          </h1>
          <p style={{ fontSize: '0.875rem', opacity: 0.75, margin: '0 0 1.5rem' }}>
            Ha fallado algo antes de poder pintar la aplicacion. Reintenta; si sigue igual,
            avisa a quien la administra.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              height: '2.75rem',
              padding: '0 1.25rem',
              borderRadius: '0.5rem',
              border: '1px solid currentColor',
              background: 'transparent',
              color: 'inherit',
              font: 'inherit',
              cursor: 'pointer',
            }}
          >
            Reintentar
          </button>
          {error.digest && (
            <p style={{ fontSize: '0.75rem', opacity: 0.6, marginTop: '1.5rem' }}>
              Referencia: {error.digest}
            </p>
          )}
        </div>
      </body>
    </html>
  );
}

# Guía del proyecto para Claude Code

**Zentra+**: gestión operativa para restaurantes, bares y cafeterías, **multisucursal desde
el modelo de datos**. `web/` es Next.js 16 (App Router) y `api/` es FastAPI con Python 3.13.
Un solo `.env` en la raíz.

**La aplicación corre en contenedores** (`docker compose`: `web`, `api`, `db`) con el código
montado como volumen, así que al guardar un archivo se recarga solo. **Las herramientas corren
en la máquina** (pruebas, linter, tipos) y no necesitan Docker.

## Comandos

```bash
pnpm run setup           # .env + dependencias + contenedores + espera a la API
pnpm dev                 # docker compose up: web :3000, api :8000 (docs /api/docs)
pnpm run dev:build       # reconstruye las imágenes (tras cambiar dependencias)
pnpm stop                # apaga los contenedores
pnpm run logs            # logs en vivo (logs:api, logs:web)

pnpm test                # pytest + vitest, en la máquina
pnpm lint                # ruff (api) + oxlint (web)
pnpm run typecheck       # tsc --noEmit
pnpm run check:secrets   # busca credenciales filtradas
```

Sin Docker: `pnpm run db:up` levanta solo PostgreSQL y `pnpm run dev:host` corre las dos
aplicaciones como procesos locales.

## Dónde va cada cosa

| Necesitas… | Archivo |
| --- | --- |
| Un endpoint nuevo | `api/app/api/routes/<módulo>.py` + registrarlo en `api/app/api/router.py` |
| Una tabla nueva | `api/app/models/<módulo>.py` (tabla + esquemas juntos) + exportarla en `api/app/models/__init__.py` |
| Lógica de negocio | `api/app/services/`. Si es aritmética o una decisión pura, `api/app/domain/`, que no importa SQLModel y se prueba sin base |
| Una migración | `pnpm run db:revision "lo que cambia"`, **leerla**, y `pnpm run db:migrate` |
| Una pantalla nueva | `web/src/app/…/page.tsx` |
| Llamar a la API | Un módulo en `web/src/services/`, nunca `fetch` dentro de un componente |
| Un tipo de la API | `web/src/types/api.ts` (DTO en snake_case + modelo de dominio en camelCase) |
| Una variable de entorno | `.env.example` **y** `api/app/core/config.py` (o `web/src/lib/env.ts` si es `NEXT_PUBLIC_*`) |

## Convenciones

- **Identificadores y contrato de la API en inglés; todo lo que lee una persona, en español.**
  Los mensajes de error de la API son interfaz, no un detalle técnico: van en español.
  Comentarios, documentación y mensajes de commit, también.
- **Las rutas del web van en español** (`/salon`, `/caja`, `/cocina`) porque el personal las
  ve; **las de la API en inglés** (`/api/orders`, `/api/shifts`) porque son el contrato.
- **`services/` es la única capa que habla con la API.** Usa `apiFetch` de
  `web/src/services/http.ts`: pone la base, manda la cookie y normaliza los errores.
- **DTO → dominio en el service**, campo a campo. La API devuelve snake_case y fechas como
  cadena; la interfaz consume camelCase y `Date`.
- **Python**: nombres del dominio en español cuando son del dominio, en inglés cuando son de
  FastAPI o SQLModel. `ruff` manda (línea de 100).
- Las pruebas viven **al lado de lo que prueban** en el web, y en `api/tests/` en la API.
- Commits con [Conventional Commits](https://www.conventionalcommits.org/) **en español**, y
  el resumen dice el síntoma o la decisión, no el diff. Ver `.gitmessage`.

## Decisiones ya tomadas (no re-discutir)

- **Sin Turborepo.** Con la API en Python solo quedaría un workspace que orquestar. Los
  scripts de la raíz hacen lo mismo sin una herramienta más. Si algún día hay dos paquetes JS,
  añadirlo son 20 líneas.
- **Un solo origen.** El navegador pide `/api/...` a su propio origen y el servidor de Next lo
  reenvía. Es lo que permite que la cookie de sesión sea `sameSite=strict` sin atributo
  `domain`, que es la forma de cookie que no viaja a ningún otro sitio.
- **El reenvío es un route handler, no un `rewrite`.** Los rewrites se resuelven al compilar y
  la dirección de la API quedaría dentro de la imagen. `web/src/app/api/[...ruta]/route.ts`
  lee `API_INTERNAL_URL` en cada petición, así que la misma imagen sirve para todos los
  entornos.
- **El esquema sale de Alembic desde el primer modelo.** Nada de crear tablas al arrancar: una
  base de desarrollo que se sincroniza sola hace que la primera migración de verdad salga con
  un diff vacío y los entornos divergen en silencio.
- **Los índices parciales se escriben a mano** en la migración y quedan fuera del autogenerate
  (`include_object` en `alembic/env.py`). Alembic no compara `postgresql_where` de forma
  fiable y propondría borrarlos y recrearlos en cada revisión.
- **El dinero es `numeric(10,2)` y `Decimal`.** Nunca `float`. El truco de guardar centavos
  enteros existe porque JavaScript no tiene decimales; Python sí. En el navegador sí se usan
  centavos enteros, y `moneyFromApi()` es el único sitio que convierte.
- **Todo total autoritativo lo calcula el servidor.** Un importe que viaja en el cuerpo de una
  petición de cobro es un cobro hecho con un precio que puede estar viejo.
- **Cada Dockerfile se despliega solo.** Docker Compose es únicamente para desarrollo. La base
  la pone Supabase: `DATABASE_URL` al pooler y `DIRECT_URL` a la conexión directa para las
  migraciones — el pooler no mantiene la sesión entre sentencias y un `alembic upgrade` por
  ahí falla a medias.
- **Las migraciones no se aplican al arrancar.** Es un paso explícito, para que dos instancias
  levantándose a la vez no compitan por el mismo `ALTER TABLE`.

## Prohibido

Tres cosas, y las tres por un motivo concreto:

1. **Ninguna tabla operativa sin `branch_id`.** Añadirlo después es una migración con relleno
   sobre quince tablas, más cada consulta, cada índice único y cada prueba.
2. **Ningún importe en `float`.** El día que el arqueo falle por dos centavos hay que migrar
   cada columna, cada cálculo y cada agregado, y los datos ya escritos no se recuperan.
3. **Nunca `echo=True` en el engine, ni subir el logger de `sqlalchemy.engine` a `INFO`.** El
   registro de sentencias incluye los parámetros enlazados, así que un insert fallido en la
   tabla de usuarios dejaría un hash de credencial en `docker logs`. Por lo mismo, nunca se
   registra `str(excepción)` de un error de base de datos: hay `describir()` en
   `app/core/conflicts.py`, que elige los campos uno a uno.

## Al terminar una tarea

1. `pnpm test` y `pnpm lint` en verde.
2. Si tocaste la API, compruébalo en `/api/docs` o con `curl`.
3. Si tocaste el modelo de datos, que `pnpm run db:migrate` siga funcionando desde una base
   vacía.
4. Los commits hechos con asistencia de IA llevan el trailer `Co-Authored-By:` para que el
   historial lo refleje.

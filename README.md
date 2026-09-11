# Zentra+

Gestión operativa para restaurantes, bares y cafeterías: comandas, salón, cocina en vivo,
caja con arqueo, catálogo y existencias. **Multisucursal desde el modelo de datos**: un
negocio, varias sucursales, catálogo compartido y operación separada.

| Capa | Herramientas |
| --- | --- |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| API | Python 3.13, FastAPI, SQLModel, Pydantic, Alembic |
| Base de datos | PostgreSQL 18 en local · Supabase en producción |
| Herramientas | pnpm, uv, Docker Compose, Vitest, pytest, ruff, oxlint |

## Puesta en marcha

Hace falta [Docker](https://www.docker.com/products/docker-desktop/),
[Node 22+](https://nodejs.org), [pnpm](https://pnpm.io/installation) y
[uv](https://docs.astral.sh/uv/getting-started/installation/). Python y PostgreSQL no: los
traen los contenedores.

```bash
pnpm run setup     # .env, dependencias, contenedores y espera a que la API responda
```

| Servicio | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| API | http://localhost:8000/api/health |
| Documentación de la API | http://localhost:8000/api/docs |
| PostgreSQL | localhost:5432 |

> `pnpm run setup`, con `run`: `pnpm setup` a secas es un comando propio de pnpm y hace otra cosa.

**La aplicación vive en los contenedores; las herramientas, en tu máquina.** `pnpm test`,
`pnpm lint` y `pnpm run typecheck` no necesitan Docker.

```bash
pnpm dev            # los contenedores con los logs en vivo
pnpm stop           # apagar
pnpm run dev:build  # reconstruir (después de cambiar dependencias)
```

También se puede levantar solo la base y correr las dos aplicaciones en la máquina:

```bash
pnpm run db:up      # solo PostgreSQL
pnpm run dev:host   # api y web como procesos locales
```

## Un solo origen

El navegador habla **siempre con su propio origen**: pide `/api/...` y el servidor de Next lo
reenvía a la API. No es comodidad, es lo que permite que la cookie de sesión sea
`sameSite=strict` sin atributo `domain`, que es la forma de cookie que no viaja a ningún otro
sitio.

El reenvío vive en `web/src/app/api/[...ruta]/route.ts` y **resuelve el destino en cada
petición**, leyendo `API_INTERNAL_URL`. Un `rewrite` de `next.config.ts` no serviría: se
resuelve al compilar, así que la dirección de la API quedaría dentro de la imagen y cambiar de
entorno obligaría a reconstruirla.

## Despliegue

Cada aplicación se despliega desde **su propio Dockerfile**, y la base de datos la pone
**Supabase**. Docker Compose es solo para desarrollo.

```bash
pnpm run docker:api   # docker build --target prod ./api
pnpm run docker:web   # docker build --target prod -f web/Dockerfile .
```

Dos cosas de Supabase que conviene no descubrir en caliente:

- `DATABASE_URL` apunta al **pooler** (puerto 6543), que es el que aguanta muchas conexiones
  cortas. Detrás de él no se pueden usar sentencias preparadas, y la API lo detecta por la
  forma de la URL y las apaga sola.
- `DIRECT_URL` apunta a la **conexión directa** (puerto 5432) y es la que usan las migraciones.
  El pooler no mantiene la sesión entre sentencias, así que un `alembic upgrade` por ahí falla
  a medias y deja el esquema en un estado intermedio.

Las migraciones **no se aplican al arrancar**: son un paso explícito, para que dos instancias
levantándose a la vez no compitan por el mismo `ALTER TABLE`.

## Estructura

```
.
├── api/                  API (FastAPI)
│   ├── app/
│   │   ├── api/routes/   Un archivo por módulo del dominio
│   │   ├── core/         Configuración, seguridad, dependencias
│   │   ├── db/           Motor, sesión y tipos de columna
│   │   ├── models/       Tablas (SQLModel) y esquemas
│   │   └── main.py       Arranque
│   ├── alembic/          Migraciones
│   └── tests/            pytest
├── web/                  Frontend (Next.js)
│   └── src/
│       ├── app/          Rutas del App Router
│       ├── services/     Única capa que habla con la API
│       ├── types/        DTO de la API y modelos de dominio
│       └── lib/          Entorno y utilidades
├── .env.example          Única fuente de variables de entorno
└── docker-compose.yml    Desarrollo: web + api + base
```

## Credenciales fuera del repositorio

El `.env` está en `.gitignore` y no se versiona. Además hay un guardián:

```bash
pnpm run check:secrets          # revisa todo lo rastreado
git config core.hooksPath .githooks   # y lo engancha al pre-commit
```

El hook **no se instala solo**: un repositorio que ejecuta código en tu máquina nada más
clonarlo es exactamente lo que no conviene normalizar. Es una línea, y se corre una vez por
clon.

## Licencia

MIT. Ver [LICENSE](LICENSE).

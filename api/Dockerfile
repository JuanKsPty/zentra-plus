# ---------------------------------------------------------------------------
#  Imagen de la API. Dos destinos:
#    dev  -> uvicorn --reload, con el codigo montado como volumen
#    prod -> el codigo copiado dentro, sin recarga
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # El entorno vive FUERA de /app: si estuviera en /app/.venv, el volumen del
    # codigo lo taparia con el .venv del host, que esta compilado para macOS.
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

WORKDIR /app

# Primero el manifiesto y el lockfile: mientras no cambien, esta capa se reusa
# y `docker build` no vuelve a bajar nada.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-install-project

# ---- desarrollo -----------------------------------------------------------
FROM base AS dev
RUN uv sync --locked --no-install-project --group dev
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# ---- produccion -----------------------------------------------------------
FROM base AS prod
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# No corre como root.
RUN useradd --create-home --uid 1001 zentra && chown -R zentra:zentra /app
USER zentra

EXPOSE 8000
# Apunta a /api/health y NO a /api/ready: health no toca la base a proposito,
# porque un proceso sano no debe reiniciarse por un parpadeo de Postgres.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health').status==200 else 1)"

# Las migraciones NO se aplican al arrancar: son un paso explicito de despliegue,
# para que dos instancias arrancando a la vez no compitan por el mismo ALTER TABLE.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

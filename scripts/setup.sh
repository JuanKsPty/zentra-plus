#!/usr/bin/env bash
# Deja Zentra+ listo y corriendo desde cero.
#
#     pnpm run setup
#
# Con "run": `pnpm setup` a secas es un comando propio de pnpm y hace otra cosa.
set -euo pipefail

cd "$(dirname "$0")/.."

azul() { printf '\033[36m%s\033[0m\n' "$1"; }
ok() { printf '\033[32m  ok\033[0m %s\n' "$1"; }
aviso() { printf '\033[33m  !\033[0m %s\n' "$1"; }
error() {
  printf '\033[31mError:\033[0m %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null || error "hace falta Docker. https://docs.docker.com/get-docker/"
docker info >/dev/null 2>&1 || error "el demonio de Docker no responde. Abre Docker Desktop y reintenta."
command -v pnpm >/dev/null || error "hace falta pnpm. https://pnpm.io/installation"
command -v uv >/dev/null || error "hace falta uv. https://docs.astral.sh/uv/getting-started/installation/"

azul "1/5  Preparando el .env"
if [ -f .env ]; then
  ok ".env ya existe, no se toca"
else
  cp .env.example .env
  # Secretos distintos y de verdad desde el primer arranque. Que sean iguales
  # haria que un token de acceso valiera como token de refresco.
  secreto=$(openssl rand -hex 32)
  refresco=$(openssl rand -hex 32)
  # -i '' es la forma de BSD (macOS); en GNU basta -i. Se prueban las dos.
  sed -i '' "s|^JWT_SECRET=.*|JWT_SECRET=${secreto}|" .env 2>/dev/null ||
    sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${secreto}|" .env
  sed -i '' "s|^JWT_REFRESH_SECRET=.*|JWT_REFRESH_SECRET=${refresco}|" .env 2>/dev/null ||
    sed -i "s|^JWT_REFRESH_SECRET=.*|JWT_REFRESH_SECRET=${refresco}|" .env
  ok ".env creado, con secretos nuevos"
fi

azul "2/5  Instalando dependencias del frontend"
pnpm install --silent
ok "node_modules listo"

azul "3/5  Instalando dependencias de la API"
uv sync --directory api --quiet
ok "entorno de Python listo"

azul "4/5  Levantando los contenedores"
docker compose up -d --build
ok "db, api y web en marcha"

azul "5/5  Esperando a que la API responda"
intentos=0
until curl -fsS http://localhost:8000/api/health >/dev/null 2>&1; do
  intentos=$((intentos + 1))
  [ "$intentos" -gt 60 ] && error "la API no respondio en 60s. Mira: pnpm run logs:api"
  sleep 1
done
ok "la API responde"

printf '\n'
azul "Listo."
printf '  Frontend       http://localhost:3000\n'
printf '  API            http://localhost:8000/api/health\n'
printf '  Documentacion  http://localhost:8000/api/docs\n\n'
printf 'Logs en vivo:  pnpm run logs      Apagar:  pnpm stop\n'

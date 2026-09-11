#!/usr/bin/env bash
# Busca credenciales filtradas en el repositorio.
#
#     pnpm run check:secrets            todo lo rastreado
#     bash scripts/check-secrets.sh --staged   solo lo que va a entrar en el commit
#
# No pretende ser un escaner de verdad: pretende que un .env o una clave pegada
# sin pensar no llegue a un repositorio publico.
set -uo pipefail

cd "$(dirname "$0")/.."

rojo() { printf '\033[31m%s\033[0m\n' "$1"; }
verde() { printf '\033[32m%s\033[0m\n' "$1"; }

SOLO_STAGED=0
[ "${1:-}" = "--staged" ] && SOLO_STAGED=1

if [ "$SOLO_STAGED" -eq 1 ]; then
  archivos=$(git diff --cached --name-only --diff-filter=ACM)
else
  archivos=$(git ls-files)
fi

[ -z "$archivos" ] && { verde "Nada que revisar."; exit 0; }

hallazgos=0

# 1. Un .env versionado. El caso mas comun y el mas caro.
for archivo in $archivos; do
  case "$archivo" in
    .env | .env.*)
      [ "$archivo" = ".env.example" ] && continue
      rojo "  $archivo  — un .env no se versiona nunca"
      hallazgos=$((hallazgos + 1))
      ;;
  esac
done

# 2. Patrones de credencial. Se excluyen .env.example y este mismo archivo, que
#    contienen los patrones a proposito y si no se denunciarian solos.
patrones='(-----BEGIN [A-Z ]*PRIVATE KEY-----)'
patrones="$patrones|(sk-[A-Za-z0-9_-]{20,})"
patrones="$patrones|(gh[pousr]_[A-Za-z0-9]{20,})"
patrones="$patrones|(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.)"
patrones="$patrones|(AKIA[0-9A-Z]{16})"
# Una URL de Postgres con contrasena de verdad (se permiten las de ejemplo).
patrones="$patrones|(postgres(ql)?(\+[a-z]+)?://[^:@/[:space:]]+:[^@/[:space:]]{8,}@)"

for archivo in $archivos; do
  case "$archivo" in
    .env.example | scripts/check-secrets.sh | pnpm-lock.yaml | api/uv.lock) continue ;;
  esac
  [ -f "$archivo" ] || continue

  # Se descartan solo los marcadores de posicion, y por su FORMA, no por
  # palabras sueltas: un ${VAR} de compose, un <clave> de la documentacion o el
  # postgres:postgres de desarrollo. Filtrar por la palabra "example" seria
  # comodo y taparia un secreto de verdad alojado en prod.example.net, que es
  # justo lo que se comprobo al escribir esto.
  coincidencias=$(grep -nEI "$patrones" "$archivo" 2>/dev/null |
    grep -viE '\$\{[A-Za-z_]|postgres:postgres@|<[a-z]+>|cambia-esto' || true)

  if [ -n "$coincidencias" ]; then
    rojo "  $archivo"
    # Solo el numero de linea y el tipo: imprimir la coincidencia pondria el
    # secreto en la salida de CI, que es justo lo que se quiere evitar.
    echo "$coincidencias" | cut -d: -f1 | sed 's/^/      linea /'
    hallazgos=$((hallazgos + 1))
  fi
done

if [ "$hallazgos" -gt 0 ]; then
  printf '\n'
  rojo "Se encontraron $hallazgos archivos sospechosos."
  echo "Si es un falso positivo, anade el archivo a la lista de exclusiones del script."
  exit 1
fi

verde "Sin credenciales a la vista."

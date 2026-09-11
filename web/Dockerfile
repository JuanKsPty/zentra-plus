# ---------------------------------------------------------------------------
#  Imagen del frontend. El contexto de build es la RAIZ del monorepo, porque el
#  lockfile y el pnpm-workspace.yaml viven alli:
#
#      docker build -f web/Dockerfile --target prod -t zentra-web .
#
#  Dos destinos:
#    dev  -> next dev, con el codigo montado como volumen
#    prod -> salida standalone servida por node, lista para desplegar sola
# ---------------------------------------------------------------------------
FROM node:24-alpine AS base
ENV PNPM_HOME=/pnpm PATH="/pnpm:$PATH"
RUN corepack enable
WORKDIR /repo

# ---- dependencias ---------------------------------------------------------
FROM base AS deps
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY web/package.json web/
RUN pnpm install --frozen-lockfile --filter web...

# ---- desarrollo -----------------------------------------------------------
FROM deps AS dev
WORKDIR /repo/web
EXPOSE 3000
CMD ["pnpm", "dev"]

# ---- compilacion ----------------------------------------------------------
FROM deps AS build
COPY web ./web
# Se hornea en el bundle del navegador AQUI, al compilar. Cambiarla obliga a
# reconstruir la imagen: no basta con reiniciar el contenedor.
ARG NEXT_PUBLIC_API_URL=""
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN pnpm --filter web build

# ---- produccion -----------------------------------------------------------
FROM base AS prod
ENV NODE_ENV=production
WORKDIR /app

# La salida standalone trae su propio node_modules recortado.
COPY --from=build /repo/web/.next/standalone ./
# .next/static y public NO estan dentro de standalone y hay que copiarlos
# aparte. Sin esto la pagina carga sin estilos, y solo se nota pidiendo un
# asset: el HTML llega igual de bien.
COPY --from=build /repo/web/.next/static ./web/.next/static
COPY --from=build /repo/web/public ./web/public

RUN addgroup -g 1001 zentra && adduser -u 1001 -G zentra -D zentra
USER zentra

ENV HOSTNAME=0.0.0.0 PORT=3000
EXPOSE 3000
CMD ["node", "web/server.js"]

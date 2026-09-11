# Hoja de ruta

Siete fases. Cada una deja algo que se puede enseñar, y ninguna se cierra sin que el recorrido
de su columna funcione de verdad.

Las casillas se marcan cuando el trabajo está hecho **y comprobado**, y cada fase lleva una
nota de lo que cambió respecto al plan: un plan que no cambia es un plan que nadie usó.

---

## Fase 0 — Cimientos

> El repositorio arranca con un comando y los contratos transversales ya están decididos.

- [x] Monorepo `api/` + `web/`, sin Turborepo
- [x] Docker Compose para desarrollo, con recarga en caliente
- [x] Dockerfile propio por aplicación, cada uno desplegable solo
- [x] Guardián de secretos y hook de pre-commit
- [x] Formato de error único, con los errores de validación traducidos campo a campo
- [x] Paginación en una sola convención, con tope duro
- [x] Las piezas de la idempotencia: conflictos por SQLSTATE, hora del dispositivo, cuerpos de reenvío
- [x] CI que comprueba la imagen en marcha
- [x] `CLAUDE.md`, `README.md` y esta hoja de ruta

*Cambió sobre el plan:* el reenvío de `/api` iba a ser un `rewrite` de `next.config.ts`.
Se descubrió probándolo que los rewrites se hornean al compilar, así que la imagen salía con
la dirección de la API dentro. Es un route handler.

*También:* la idempotencia iba a ser una tabla genérica de claves. Se quedó en leer-antes-de-
escribir, que es lo que funciona cuando la operación ya tiene identidad propia — y la comanda
la tiene, porque el identificador lo acuña el dispositivo.

## Fase 1 — Columna vertebral

> El sistema sabe quién eres, de qué sucursal y qué puedes tocar.

- [ ] Negocio y sucursales, con `branch_id` en todo el esquema operativo
- [ ] Sesión por correo y sesión por PIN, con refresco y rotación
- [ ] RBAC que niega por defecto, con el permiso declarado en cada ruta
- [ ] Alcance por sucursal imposible de olvidar
- [ ] Configuración del negocio
- [ ] Cáscara del web: tema, tipografía y navegación filtrada por permisos
- [ ] Dos puertas de entrada: correo para el panel, PIN para el piso

**Se demuestra:** entrar por correo con el dueño, entrar por PIN con un mesero, y comprobar
que una ruta sin permiso devuelve 403 y que la interfaz ni siquiera la ofrece.

## Fase 2 — Catálogo y salón

> El negocio describe qué vende y dónde se sienta la gente.

- [ ] Categorías, productos y modificadores, a nivel negocio
- [ ] Precio y disponibilidad por sucursal
- [ ] Sectores y mesas, con el estado del salón como fuente de verdad
- [ ] Mapa del salón: dibujar, editar y guardar en bloque

**Se demuestra:** crear una categoría, tres productos con modificadores y un sector con cuatro
mesas desde el panel, y verlas en el mapa.

## Fase 3 — Servicio en vivo

> Un mesero toma una comanda y la cocina la ve al instante.

- [ ] Órdenes con máquina de estados e historial
- [ ] Número de cuenta por sucursal
- [ ] El identificador lo pone el dispositivo: reenviar no duplica
- [ ] WebSocket por sucursal
- [ ] Vista del mesero: salón, comanda y envío a cocina
- [ ] Tablero de cocina por columnas

**Se demuestra:** dos navegadores lado a lado. En uno se envía una comanda; en el otro aparece
en cocina **sin recargar**.

## Fase 4 — Dinero

> El cajero cobra y el turno cuadra.

- [ ] Cobro con pagos divididos, propina y liberación de la mesa
- [ ] Turnos de caja con arqueo
- [ ] Venta de mostrador en una sola petición

**Se demuestra:** abrir turno, cobrar una cuenta en dos pagos con propina, hacer una venta de
mostrador, cerrar turno y comprobar que la diferencia del arqueo es cero.

## Fase 5 — Existencias, panel y reportes

> El dueño ve qué pasó y qué queda.

- [ ] Existencias por producto, que bajan al cerrar la cuenta
- [ ] Panel de métricas del día
- [ ] Exportación a CSV

**Se demuestra:** vender un producto con existencias y verlas bajar; descargar el CSV del
rango y abrirlo con los acentos bien.

## Fase 6 — Endurecimiento y cierre

> De maqueta a producto.

- [ ] `/api/ready`, que sí toca la base
- [ ] Registro estructurado con el identificador de la petición en cada línea
- [ ] Límite de peticiones y bloqueo por intentos
- [ ] Cabeceras de seguridad y CORS validado al arrancar
- [ ] Un recorrido completo en un navegador de verdad
- [ ] Auditoría de seguridad con los riesgos aceptados, escritos

**Se demuestra:** el CI en verde, incluido el paso que para PostgreSQL y exige que
`/api/ready` dé 503 mientras `/api/health` sigue en 200.

---

## Fuera del alcance inicial

No por olvido. Cada uno es un módulo entero, y ninguno es lo que hace falta demostrar primero:

- **Modo sin conexión y PWA.** Lo más caro de todo. El servidor ya está preparado —la
  idempotencia entró en la fase 0— así que añadirlo no obliga a reescribir el dominio.
- **Recetas, insumos, proveedores y movimientos de stock.** Las existencias por producto
  cubren el caso frecuente: hay productos que *son* la unidad que se cuenta.
- **Menú por QR y pedido del cliente.**
- **Descuentos con aprobación** y **fusión de cuentas.**
- **Bitácora de auditoría.**
- **Interfaz multisucursal**: selector, asignación de personal y panel consolidado. El esquema
  ya lo soporta desde la fase 1; lo que falta son pantallas.

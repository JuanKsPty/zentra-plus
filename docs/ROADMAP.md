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

- [x] Sucursales, con el contador de número de cuenta por sede
- [x] Sesión por correo y sesión por PIN, con refresco y rotación
- [x] RBAC que niega por defecto, con el permiso declarado en cada ruta
- [x] Alcance por sucursal imposible de olvidar
- [x] Configuración del negocio
- [x] Cáscara del web: tema, tipografía y navegación filtrada por permisos
- [x] Dos puertas de entrada: correo para el panel, PIN para el piso

**Se demuestra:** entrar por correo con el dueño, entrar por PIN con un mesero, y comprobar
que una ruta sin permiso devuelve 403 y que la interfaz ni siquiera la ofrece.

*Cambió sobre el plan:* estaba previsto un commit de arreglo para la colisión de dos inicios
de sesión en el mismo segundo. No hizo falta: el `jti` es la clave primaria de la tabla de
refrescos, así que la colisión es imposible por estructura y no algo que haya que evitar. El
arreglo que sí apareció fue otro — al caducar el token, ninguna petición del cliente se
renovaba.

*También:* ni la navegación ni el aterrizaje por rol listan rutas sin pantalla. Las dos listas
lo intentaron y sus pruebas se pusieron rojas; tenían razón, así que cada destino entra en el
mismo commit que su pantalla. El orden previsto completo del aterrizaje se conserva aparte,
con su prueba, porque el razonamiento del orden es lo que se pierde primero.

## Fase 2 — Catálogo y salón

> El negocio describe qué vende y dónde se sienta la gente.

- [x] Categorías y productos, a nivel negocio
- [x] Precio y disponibilidad por sucursal
- [x] Sectores y mesas, con el estado del salón como fuente de verdad
- [x] El mapa se guarda en bloque, en una sola petición
- [x] Catálogo y salón visibles desde el panel
- [ ] Modificadores: el modelo está, faltan endpoints y pantalla
- [ ] Editar el catálogo desde el panel (hoy es solo lectura)

**Se demuestra:** `pnpm run seed --demo` crea la carta y doce mesas; el panel las muestra, la
búsqueda filtra y el precio que aparece es el de la sucursal activa.

*Cambió sobre el plan:* el `branch_id` se ponía después de construir el modelo y la validación
ocurre al construir, así que `fijar_sucursal` pasó a ser `crear_en_sucursal`, un constructor.

*Y dos trampas que costaron encontrar:* el autogenerate de Alembic propuso **borrar** el índice
de fila única de la configuración —lo ve en la base, no lo encuentra en los modelos porque va
sobre una expresión, y concluye que sobra—; y un componente de servidor no tiene tarro de
galletas, así que `credentials: 'include'` no manda nada y la API respondía 401 a todo.

## Fase 3 — Servicio en vivo

> Un mesero toma una comanda y la cocina la ve al instante.

- [x] Órdenes con máquina de estados e historial
- [x] Número de cuenta por sucursal, sin repetirse ni dejar huecos
- [x] El identificador lo pone el dispositivo: reenviar no duplica
- [x] Canal de avisos por sucursal
- [x] Vista del mesero: salón, tomar comanda y detalle
- [x] Tablero de cocina por columnas, con cronómetro
- [ ] Modificadores en la comanda (el modelo está, falta la pantalla)

**Se demuestra:** se abre el canal, otro cliente toma una comanda, y llegan los dos avisos —la
comanda y la mesa— sin recargar y por el mismo origen.

*Cambió sobre el plan, y es el cambio más grande de todas las fases:* **el WebSocket no
atraviesa**. El navegador habla con su propio origen y el servidor de Next reenvía `/api`, pero
ese reenvío es un route handler y un route handler no puede atravesar el *upgrade* de un
WebSocket. Con Dockerfiles separados y sin proxy de borde —las dos cosas que este proyecto
eligió— el socket no llega.

Se cambió el transporte a **SSE**, que es una respuesta HTTP normal y pasa por el mismo camino
que todo lo demás. Encaja mejor: el evento es una señal, no un canal de datos. Y desaparece el
pase de un solo uso que el WebSocket necesitaba, porque la cookie viaja como en cualquier
petición.

*También:* estaba previsto un commit de arreglo para «el canal aceptaba conexiones sin mirar el
token». No hizo falta — el canal nunca existió sin comprobarlo. El que sí apareció fue otro:
`/comanda/nueva` la capturaba la ruta dinámica y el mesero veía un 404 al tocar una mesa libre.

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

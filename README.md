# Teleconsulta

Aplicación web (monolito Django) para preparar e iniciar una teleconsulta entre
paciente y profesional, con sala de espera, intake pre-consulta y actualización
de estado en tiempo real vía WebSockets.

## Stack

- **Django 6.1** (monolito, ORM + Django Admin)
- **Django Channels** + Daphne (WebSockets sobre ASGI, mismo proceso que el HTTP)
- **SQLite** por defecto (persistencia real en disco, no en memoria). Se puede
  apuntar a Postgres seteando la variable de entorno `DATABASE_URL` (requiere
  `pip install dj-database-url`), sin tocar código.
- Templates de Django + JS vanilla (un `WebSocket` nativo por vista) — no hay
  frontend separado, es un monolito delgado.
- Tailwind vía CDN solo para estilos, no hay build step de frontend.

## Cómo correrlo en local

```bash
python3 -m venv venv
source venv/bin/activate        # en Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo      # crea usuarios y consultas de demo
python manage.py runserver      # alcanza para probar todo (WS incluido)
```

> `runserver` en Django 5+/6 sirve ASGI automáticamente si `ASGI_APPLICATION`
> está configurado (como es el caso acá), así que no hace falta Daphne para
> desarrollo. Para algo más cercano a producción: `daphne -b 0.0.0.0 -p 8000
> config.asgi:application`.

### Usuarios de demo (contraseña `demo1234` para todos)

| Usuario        | Rol          | Uso                                             |
|----------------|--------------|--------------------------------------------------|
| `admin`        | Admin        | Entra a `/panel/` y gestiona consultas/usuarios  |
| `paciente1`    | Paciente     | Sala de espera de la consulta #1                 |
| `paciente2`    | Paciente     | Sala de espera de la consulta #2                 |
| `profesional1` | Profesional  | Ve ambas consultas (#1 y #2) asignadas           |

## Cómo probar el flujo completo

1. Entrar como **admin** en `http://localhost:8000/login/`. Se lo redirige a
   `/panel/consultas/`, su panel propio (ver sección "Panel de admin" más
   abajo) — **ya no es el Django Admin (`/admin/`)**. Ahí, **"+ Nueva
   consulta"** → elegir paciente y profesional (los combos ya filtran por rol
   y, si el profesional marcó que no está disponible, tampoco aparece — ver
   Tarea de disponibilidad) y guardar.
2. Abrir otra pestaña/navegador (o modo incógnito) y entrar como **paciente1**
   en `http://localhost:8000/login/`. Se lo redirige a su sala de espera.
3. Completar el formulario de intake (motivo, fecha de nacimiento,
   consentimiento, medicamentos, alergias) y guardar. La pantalla muestra
   **blockers** (impiden iniciar, ej. falta consentimiento) y **warnings**
   (no bloquean, ej. falta la fecha de nacimiento) en tiempo real, sin
   recargar.
4. En una tercera pestaña, entrar como **profesional1**. Ve la información
   del paciente, sus blockers/warnings, y si el paciente ya está en la sala
   el estado sube a "Ambos presentes" automáticamente (visible al instante en
   la pestaña del paciente también, vía WebSocket).
5. El profesional presiona **"Iniciar consulta"** (solo habilitado cuando el
   estado es `both_present`) y luego **"Finalizar consulta"**.
6. Todo el tiempo, los cambios de estado se propagan por WebSocket
   (`/ws/consultations/<id>/`) a ambas pantallas sin refrescar.

## Panel de admin (`/panel/`)

El rol admin (`user.is_staff`) ya **no** usa el Django Admin (`/admin/`) como
flujo principal — tiene su propio panel, con el mismo sistema de diseño que
el resto de la app:

- **`/panel/consultas/`** — lista todas las teleconsultas; **"+ Nueva
  consulta"** (`/panel/consultas/nueva/`) reusa `ConsultationCreateForm`
  (mismos filtros de rol y disponibilidad de siempre).
- **`/panel/usuarios/`** — lista todos los `User`, con su rol (paciente/
  profesional/admin) y si están activos. Desde ahí:
  - **"+ Nuevo usuario"** (`/panel/usuarios/nuevo/`): username, nombre,
    contraseña y rol — incluyendo "Admin" (marca `is_staff`, sin
    `UserProfile`).
  - **"Editar"**: nombre, rol (migra el `UserProfile` si cambia de paciente
    a profesional o viceversa) y contraseña opcional (vacía = no la cambia).
  - **"Desactivar" / "Reactivar"**: pone `is_active=False`/`True`. Django ya
    respeta esto para el login. **Nunca se borra un `User`** — `Consultation`
    usa `on_delete=PROTECT` en `patient`/`professional` a propósito, así que
    borrar rompería la integridad de las consultas ya creadas; desactivar es
    la forma correcta y reversible de sacar a alguien de circulación.

`/admin/` (Django Admin) sigue activo en `config/urls.py`, pero solo para
debugging directo de la base de datos durante desarrollo — ya no tiene
registrado nada de `consultations` (ver `consultations/admin.py`), y
`accounts/admin.py` dejó de personalizarlo (usa el `UserAdmin` por defecto).

### Disponibilidad del profesional

`UserProfile.is_available` (default `True`) controla si un profesional
aparece como opción al crear una consulta **nueva** — no afecta las
consultas que ya tiene asignadas. Cada profesional ve un switch en
`/profesional/` para prenderla/apagarla, que guarda al toque vía
`POST /profesional/disponibilidad/` (fetch, sin recargar).

## Diseño / decisiones técnicas

- **Capas separadas**: `views.py` es delgado (HTTP in/out); toda la regla de
  negocio vive en `consultations/services/`:
  - `readiness.py` → `ReadinessService` decide blockers/warnings a partir de
    un `IntakeForm`. Es una clase de dominio pura, sin dependencias de Django
    más allá de lo que recibe como argumento — fácil de testear.
  - `state_machine.py` → `ConsultationStateMachine` es el **único** lugar que
    escribe `Consultation.status`. Cada método (`patient_join`,
    `submit_intake`, `professional_join`, `start`, `complete`) valida la
    transición y levanta `InvalidTransition` si no corresponde.
  - `realtime.py` → `RealtimeNotifier` traduce un cambio de estado a un
    mensaje de Channels. Se inyecta en la máquina de estados (en vez de
    importarse directo) para poder testear la máquina de estados sin
    levantar un channel layer.
- **Estados**: `scheduled → waiting_intake → ready → both_present →
  in_progress → completed`, tal como sugiere el enunciado. Reglas:
  - Solo el **paciente** dispara `patient_join` y `submit_intake` (vía las
    vistas con `@patient_required`).
  - Solo el **profesional** dispara `professional_join`, `start` y `complete`
    (vía `@professional_required`).
  - Si el paciente edita su intake y deja de cumplir un requisito bloqueante
    (ej. destilda el consentimiento), el estado retrocede a
    `waiting_intake` — no se permite iniciar con datos incompletos aunque
    antes haya estado "ready".
  - `start` solo es válido desde `both_present`; `complete` solo desde
    `in_progress`. Cualquier otro intento lanza `InvalidTransition` y se
    muestra como mensaje de error, no como excepción sin manejar.
- **Roles**: `User` nativo de Django + `UserProfile.role` (paciente/
  profesional). El rol "admin" no se modela como campo: se usa
  `user.is_staff`, que la app resuelve con su propio panel (`/panel/`, ver
  arriba) en vez de con el Django Admin. Autenticación con el login/logout
  estándar de Django (+ alta pública en `/signup/`, solo paciente/
  profesional) — no es el foco de la prueba, así que no se agregó nada más
  (JWT, 2FA, etc.).
- **Tiempo real**: un `ConsultationConsumer` (Channels) por consulta,
  agrupado en `consultation_{id}`. Cada vista (paciente y profesional) abre
  un WebSocket nativo al cargar la página; al recibir un mensaje actualiza el
  pill de estado, los blockers/warnings y el estado de los botones, sin
  polling ni recarga.

## Limitaciones conocidas

- El channel layer usado es `InMemoryChannelLayer`: funciona perfecto para
  un solo proceso (como esta demo), pero para correr con múltiples workers
  en producción habría que cambiar a `channels_redis.core.RedisChannelLayer`
  (requiere Redis) — es un cambio de una línea en `settings.py`.
- La vista del profesional no actualiza por WebSocket los *valores* del
  intake (motivo, medicamentos, etc.) si el paciente los edita después de
  que el profesional ya cargó la página — sí actualiza el estado, blockers y
  warnings. Un refresh muestra los datos más recientes.
- No se implementó ninguno de los bonuses (arquitectura/deploy, agente de
  intake en lenguaje natural, briefing con IA para el profesional, ni
  videollamada embebida).
- No hay tests automatizados (unit tests de `ReadinessService` y
  `ConsultationStateMachine` serían el primer paso natural dado que están
  aislados de Django).
- El admin puede crear una teleconsulta para cualquier par paciente/
  profesional existente desde `/panel/consultas/nueva/`, y usuarios nuevos
  (paciente, profesional o admin) desde `/panel/usuarios/nuevo/`.

## Nota sobre uso de IA

Este proyecto fue desarrollado con asistencia de Claude (Anthropic). La IA
propuso la arquitectura inicial (separación en servicios de dominio,
Channels para tiempo real, reutilizar el Django Admin como "formulario
simple" del admin) y generó el scaffolding completo: modelos, servicios
(`ReadinessService`, `ConsultationStateMachine`, `RealtimeNotifier`),
consumer/routing de Channels, vistas, forms, templates y el comando de seed.
Todo el código generado fue ejecutado y validado manualmente en este mismo
proceso: se corrieron migraciones, se levantó el servidor con Daphne y se
probó el flujo completo end-to-end con requests HTTP reales (login, envío de
intake, transición de estados) y una conexión WebSocket real para confirmar
que el profesional recibe el cambio de estado del paciente sin recargar. Las
decisiones de negocio (qué es blocker vs warning, cuándo retrocede el
estado, qué rol dispara cada transición) fueron definidas y ajustadas
manualmente a partir del enunciado, no aceptadas ciegamente de la propuesta
inicial de la IA.

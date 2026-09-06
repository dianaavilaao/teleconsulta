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
> está configurado (como es el caso aquí), así que no hace falta Daphne para
> desarrollo. Para algo más cercano a producción: `daphne -b 0.0.0.0 -p 8000
> config.asgi:application`.

### Usuarios de demo (contraseña `demo1234` para todos)

| Usuario        | Rol          | Uso                                             |
|----------------|--------------|--------------------------------------------------|
| `admin`        | Admin        | Entra a `/admin/` y crea teleconsultas           |
| `paciente1`    | Paciente     | Sala de espera de la consulta #1                 |
| `paciente2`    | Paciente     | Sala de espera de la consulta #2                 |
| `profesional1` | Profesional  | Ve ambas consultas (#1 y #2) asignadas           |

## Cómo probar el flujo completo

1. Entrar como **admin** en `http://localhost:8000/admin/` → **Consultations**
   → **Add consultation**. Elegir paciente y profesional (los combos ya filtran
   por rol) y guardar. Esto es el "formulario simple" del enunciado: se
   reutiliza el Django Admin en vez de construir un CRUD aparte.
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
    (ej. desmarca el consentimiento), el estado retrocede a
    `waiting_intake` — no se permite iniciar con datos incompletos aunque
    antes haya estado "ready".
  - `start` solo es válido desde `both_present`; `complete` solo desde
    `in_progress`. Cualquier otro intento lanza `InvalidTransition` y se
    muestra como mensaje de error, no como excepción sin manejar.
- **Roles**: `User` nativo de Django + `UserProfile.role` (paciente/
  profesional). El rol "admin" no se modela como campo: se usa
  `user.is_staff`, lo que además da acceso gratis al Django Admin.
  Autenticación con el login/logout estándar de Django — no es el foco de la
  prueba, así que no se agregó nada más (JWT, 2FA, etc.).
- **Tiempo real**: un `ConsultationConsumer` (Channels) por consulta,
  agrupado en `consultation_{id}`. Cada vista (paciente y profesional) abre
  un WebSocket nativo al cargar la página; al recibir un mensaje actualiza el
  pill de estado, los blockers/warnings y el estado de los botones, sin
  polling ni recarga.

## Bonus 2 y 3: síntomas y briefing con IA (Groq)

Dos funcionalidades opcionales que usan una API de IA gratuita ([Groq](https://groq.com),
modelo `openai/gpt-oss-20b` — configurable en `consultations/services/ai_client.py`;
formato compatible con OpenAI) para asistir —nunca reemplazar— el criterio clínico:

- **Bonus 2 — Extracción de síntomas (paciente)**: en la sala de espera, el paciente escribe
  su motivo de consulta en lenguaje natural y presiona **"Analizar síntomas"**. La IA sugiere
  síntomas (guiados por un vocabulario canónico de MedlinePlus en español, ver
  `consultations/services/symptom_vocabulary.py`) como checkboxes ya marcados, que el
  paciente puede desmarcar o completar con **"Otro"** antes de **"Confirmar síntomas"**
  (se guardan en `IntakeForm.symptoms`).
- **Bonus 3 — Briefing para el profesional**: en la sala del profesional, si el paciente ya
  confirmó síntomas, aparece **"Generar briefing"**: un resumen estructurado (síntesis,
  temas a profundizar, preguntas sugeridas, señales de alerta, datos faltantes) armado a
  partir del motivo, los síntomas, la edad, medicamentos y alergias. Se persiste en
  `Consultation.ai_briefing` para no regenerarlo en cada carga de página; el profesional
  puede pedir **"Regenerar briefing"** cuando quiera una versión nueva.

### Cómo conseguir una API key gratuita

1. Entrar a [console.groq.com](https://console.groq.com) y crear una cuenta (no pide tarjeta
   de crédito).
2. Ir a **API Keys** → **Create API Key** y copiarla.

### Cómo setearla

El proyecto usa `python-dotenv`: `config/settings.py` carga un archivo `.env` (en la raíz del
repo, no versionado — ya está en `.gitignore`) al arrancar, sin pisar variables que ya estén
seteadas en el entorno real. Ya existe un `.env` con `GROQ_API_KEY=` vacío; solo hay que
abrirlo y completar el valor:

```
GROQ_API_KEY=tu-api-key
```

y listo, `python manage.py runserver` (o `daphne`) ya la va a ver. Alternativa sin `.env`: se
puede exportar la variable directo en la terminal antes de levantar el servidor
(`export GROQ_API_KEY="tu-api-key"` / en PowerShell `$env:GROQ_API_KEY = "tu-api-key"`) —
`GROQ_API_KEY` se lee siempre con `os.environ.get` en `consultations/services/ai_client.py`,
así que cualquiera de las dos formas funciona igual.

### Limitaciones de esta parte

- Depende de un servicio externo (Groq): si no hay conexión, la API está caída, o no está
  seteada `GROQ_API_KEY`, ambas funcionalidades degradan sin romper nada — el paciente sigue
  pudiendo guardar su intake sin síntomas etiquetados, y el profesional ve un mensaje de
  error ("No se pudo generar el briefing, reintentar") en vez del briefing.
- El free tier de Groq tiene rate limits razonables para desarrollo/demo, pero no pensados
  para producción con tráfico real; un `HTTP 429` se trata como fallo recuperable (no
  rompe la página).
- Groq retira/renueva modelos con cierta frecuencia (ya nos pasó: `llama-3.3-70b-versatile`
  dejó de existir y la API empezó a responder 404 `model_not_found`). Si algún día
  `openai/gpt-oss-20b` deja de estar disponible, un `GET /v1/models` (con la key activa)
  devuelve el catálogo vigente — solo hay que actualizar `GROQ_MODEL` en
  `consultations/services/ai_client.py`.
- La calidad de los síntomas detectados y del briefing depende enteramente del modelo — no
  hay garantía de exhaustividad ni de exactitud clínica.
- **Ninguna de las dos funcionalidades reemplaza el juicio clínico del profesional**: son
  material de apoyo, puramente informativo/aditivo. No participan de `ReadinessService` ni
  de `ConsultationStateMachine` (no bloquean ni habilitan ninguna transición de estado).

## Limitaciones conocidas

- El channel layer usado es `InMemoryChannelLayer`: funciona perfecto para
  un solo proceso (como esta demo), pero para correr con múltiples workers
  en producción habría que cambiar a `channels_redis.core.RedisChannelLayer`
  (requiere Redis) — es un cambio de una línea en `settings.py`.
- La vista del profesional no actualiza por WebSocket los *valores* del
  intake (motivo, medicamentos, etc.) si el paciente los edita después de
  que el profesional ya cargó la página — sí actualiza el estado, blockers y
  warnings. Un refresh muestra los datos más recientes.
- No se implementó el bonus de arquitectura/deploy en la nube.
- No hay tests automatizados (unit tests de `ReadinessService` y
  `ConsultationStateMachine` serían el primer paso natural dado que están
  aislados de Django).
- El admin puede crear una teleconsulta para cualquier par
  paciente/profesional existente, pero no crea usuarios nuevos desde ahí
  (se crean como cualquier `User` de Django, vía admin o `seed_demo`).

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

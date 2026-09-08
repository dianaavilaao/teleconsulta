# Teleconsulta

Monolito Django para una teleconsulta entre paciente y profesional: sala de
espera con intake, validación de horarios, videollamada integrada,
diagnóstico post-consulta y estado en tiempo real vía WebSockets. Incluye dos
funcionalidades opcionales de IA (síntomas sugeridos y briefing clínico) que
asisten al profesional sin reemplazar su criterio.

## Stack

Django 6.1 + Channels/Daphne (WebSockets sobre ASGI) + SQLite (o Postgres
seteando `DATABASE_URL`, sin tocar código). Templates de Django + JS vanilla,
sin frontend separado ni build step; Tailwind vía CDN solo para estilos.

## Cómo correrlo en local

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo      # crea usuarios y consultas de demo
python manage.py runserver      # alcanza para probar todo, WS incluido
```

> `runserver` ya sirve WebSockets (Channels) sin hacer nada más: `"daphne"`
> está registrado como la primera app en `INSTALLED_APPS`, lo que hace que
> Django use el servidor ASGI de Daphne en vez del WSGI de siempre para
> `runserver` — si algún día se saca de ahí, el tiempo real deja de andar
> aunque la app siga funcionando por HTTP normal. Para correrlo explícitamente
> con Daphne (por ejemplo, algo más cercano a producción):
> `daphne -b 0.0.0.0 -p 8000 config.asgi:application`.

`SECRET_KEY` tiene un fallback de desarrollo en `config/settings.py`, así que
no hace falta setear nada para correrlo local. Antes de cualquier
despliegue real, definirla en `.env` (o el entorno) con una clave propia:
`SECRET_KEY=una-clave-larga-y-random`.

### Habilitar las funcionalidades de IA (opcional)

Sin esto la app funciona igual: el paciente guarda su intake sin síntomas
sugeridos y el profesional no ve el botón de briefing.

1. Crear una cuenta gratis en [console.groq.com](https://console.groq.com)
   (no pide tarjeta) y generar una API Key.
2. Crear un archivo `.env` en la raíz del repo (no viene versionado, está en
   `.gitignore`) con:
   ```
   GROQ_API_KEY=tu-api-key
   ```
3. Listo — `config/settings.py` la carga sola al arrancar. También se puede
   exportar como variable de entorno del sistema en vez de usar `.env`.

### Usuarios de demo (contraseña `demo1234` para todos)

| Usuario        | Rol         | Uso                                       |
|----------------|-------------|--------------------------------------------|
| `admin`        | Admin       | `/panel/` — gestiona consultas y usuarios  |
| `paciente1`    | Paciente    | Sala de espera de su consulta              |
| `profesional1` | Profesional | Ve las consultas que tiene asignadas       |

### Motivos de consulta para probar "Analizar síntomas"

Pegar cualquiera de estos como motivo de consulta en la sala de espera del
paciente, para probar la sugerencia de síntomas por IA:

```
Desde ayer he estado sintiéndome bastante mal, con un fuerte malestar general y poca energía.
He tenido un dolor intenso en la cabeza y molestias en el estómago durante gran parte del día.
También he tenido varias deposiciones líquidas y he presentado escalofríos y siento el cuerpo
más débil de lo normal. Los síntomas han ido aumentando y por eso decidí consultar para saber
qué podría estar pasando.
```

```
Desde ase unos dias tengo un dolor muy fuerte en la espalda, mas que nada en la parte de abajo
y me cuesta mucho moverme. Cuando me levanto de la cama siento como un tiron y me duele asta
para caminar o agacharme. Tambien tengo el cuello duro y me duele cuando trato de dar vuelta la
cabeza para los lados. E tomado unos remedios que tenia en la casa pero no me a echo mucho
efecto y sigo con el dolor. No se si sera por que e estado trabajando mucho y cargando cosas,
pero cada ves me duele mas.
```

El segundo tiene errores ortográficos a propósito, para comprobar que la IA
igual identifica los síntomas. 

## Cómo probar el flujo completo

1. **Admin** en `/login/` → redirige a `/panel/consultas/` → "+ Nueva
   consulta": elegir paciente, profesional y horario. Rechaza profesionales
   marcados como no disponibles y horarios que chocan con otra consulta del
   paciente o del profesional (±30 minutos).
2. **Paciente** (otra pestaña o modo incógnito) → su sala de espera →
   completar el intake (motivo, fecha de nacimiento, consentimiento,
   medicamentos, alergias). Los blockers/warnings se actualizan en tiempo
   real. Opcional: "Analizar síntomas" con uno de los motivos de arriba.
3. **Profesional** (tercera pestaña) → ve el intake del paciente; en cuanto
   ambos están en la sala, el estado sube a "Ambos presentes" al instante en
   las dos pantallas, vía WebSocket.
4. Profesional presiona **"Iniciar consulta"** → la videollamada se abre
   sola en ambas pantallas. Al terminar, **"Finalizar consulta"**.
5. Ya completada, el profesional puede registrar un **diagnóstico**
   (opcional: texto libre, seguimiento, y si hubo problemas de conexión
   durante la sesión). Al guardar, vuelve a su lista de consultas. El
   paciente puede ver el diagnóstico, las recomendaciones y si requiere
   seguimiento desde su historial (`/paciente/<id>/historial/`) — las notas
   de seguimiento y los problemas de conexión siguen siendo internos.

## Bonuses implementados

| Bonus                                  | Estado                                            |
|----------------------------------------|---------------------------------------------------|
| Agente de intake (IA sugiere síntomas) | ✅ ver "Funcionalidades de IA"                     |
| Briefing para el profesional (IA)      | ✅ ver "Funcionalidades de IA"                     |
| Videollamada                           | ✅ Jitsi Meet embebido, sincronizado por WebSocket |
| Arquitectura/deploy en la nube         | ✅ documentado aparte (no incluido en este repo)   |

## Funcionalidades de IA (Groq)

Usa la API gratuita de [Groq](https://groq.com) (modelo `openai/gpt-oss-20b`,
formato compatible con OpenAI — ver `consultations/services/ai_client.py`).
Setup arriba, en "Habilitar las funcionalidades de IA".

- **Síntomas sugeridos**: a partir del motivo de consulta en texto libre,
  sugiere hasta 10 síntomas (guiados por un vocabulario de MedlinePlus, ver
  `symptom_vocabulary.py`) como checkboxes editables antes de confirmar.
- **Briefing del profesional**: resumen del caso, hasta 3 preguntas
  sugeridas, señales de alerta y datos faltantes, a partir del intake
  completo. Se persiste (`Consultation.ai_briefing`) y se puede regenerar.
- Si Groq falla (sin red, sin API key, rate limit, modelo retirado del
  catálogo), ambas degradan sin romper nada: el paciente sigue sin síntomas
  etiquetados, el profesional ve un error en vez del briefing. Ninguna de
  las dos participa de `ReadinessService` ni de la máquina de estados.

## Panel de administración (`/panel/`)

- **`/panel/consultas/`**: lista todas las consultas, con su estado y, si
  están completadas, si tienen diagnóstico registrado y si hubo problemas de
  conexión — sin exponer el contenido clínico, que es privado del
  profesional.
- **`/panel/usuarios/`**: crear, editar rol y desactivar/reactivar usuarios.
  Nunca se borra un `User` (`Consultation` usa `on_delete=PROTECT`);
  desactivar es la forma reversible de sacarlo de circulación.
- Cada profesional controla su disponibilidad (switch en `/profesional/`) —
  afecta solo a las consultas nuevas, no a las ya asignadas.

## Diseño / decisiones técnicas

- **Capas separadas**: `views.py` es solo HTTP in/out; toda regla de negocio
  vive en `consultations/services/`, cada una con su propia excepción de
  dominio (`InvalidTransition`, `UnderageError`, `SchedulingConflict`,
  `DiagnosisNotAllowed`).
- **`ConsultationStateMachine`** es el único lugar que escribe
  `Consultation.status`: `scheduled → waiting_intake → ready → both_present
  → in_progress → completed`. El paciente dispara `patient_join`/
  `submit_intake`; el profesional, `professional_join`/`start`/`complete`.
  Si el paciente deja de cumplir un requisito bloqueante, el estado
  retrocede a `waiting_intake`.
- **`ReadinessService`** decide blockers/warnings a partir del intake — es
  una clase de dominio pura, sin dependencias de Django.
- **Tiempo real**: un `ConsultationConsumer` (Channels) por consulta; cada
  transición se notifica vía `RealtimeNotifier` (inyectado, no importado
  directo, para poder testear la máquina de estados sin channel layer).
- **Roles**: `User` nativo + `UserProfile.role`; admin = `user.is_staff`.
  Login/logout estándar de Django, sin JWT/2FA (fuera del foco de la
  prueba).

## Limitaciones conocidas

- Channel layer `InMemoryChannelLayer`: sirve para un solo proceso;
  producción con múltiples workers requeriría `channels_redis` (cambio de
  una línea en `settings.py`).
- No hay tests automatizados.

## Nota sobre uso de IA

Este proyecto fue desarrollado con asistencia de Claude (Anthropic), que generó
el scaffolding completo (modelos, servicios, Channels, vistas, forms,
templates, seed) y cada feature agregada después (validaciones de negocio,
IA, panel de admin, diagnóstico post-consulta, videollamada). Todo el código
fue validado a mano: migraciones aplicadas, flujo completo probado
end-to-end con requests HTTP y WebSockets reales. Las decisiones de negocio
(blocker vs. warning, qué rol dispara cada transición, qué es privado del
profesional vs. visible para el admin) se definieron y ajustaron
manualmente, no se aceptaron tal cual las propuso la IA.

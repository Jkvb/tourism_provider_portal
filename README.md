# tourism_provider_portal

## Política funcional obligatoria

Este módulo **NO** permite registro web inicial. Están prohibidas rutas y formularios públicos de alta inicial (`/register`, `/signup`, `/turismo/registro` o equivalentes).

El onboarding inicial de prestadores turísticos es **100% por WhatsApp** con Meta Cloud API.

## Flujo oficial (único flujo permitido)

1. El prestador escribe por WhatsApp al número del bot.
2. El bot solicita y captura su nombre completo.
3. El bot solicita y captura su foto de perfil.
4. El partner queda en revisión (`pending`) para comité.
5. El comité aprueba o rechaza en backend Odoo (menú CRM > Turismo > Solicitudes WhatsApp).
6. Si se aprueba, se crea automáticamente el usuario portal (si no existía).
7. Se envía por WhatsApp un enlace para definir contraseña.
8. El prestador accede al portal web autenticado.
9. Edita su perfil en `/my/tourism/profile`.
10. Crea publicaciones visibles en `/tourism/feed`.

## Configuración Meta Cloud API

Configurar en `Ajustes > Parámetros del sistema`:

- `tourism_provider_portal.verify_token`
- `tourism_provider_portal.access_token`
- `tourism_provider_portal.phone_number_id`
- `tourism_provider_portal.graph_api_version` (opcional, fallback `v18.0`)

## Webhook

- Verificación: `GET /whatsapp/webhook`
  - valida `hub.mode`, `hub.verify_token`, `hub.challenge`.
- Eventos: `POST /whatsapp/webhook`
  - procesa payload de Meta Cloud API y avanza estados de onboarding.

## Gestión administrativa (CRM)

Menú:

- CRM
  - Turismo
    - Solicitudes WhatsApp
    - Publicaciones

En solicitudes se revisan estados, foto, datos de WhatsApp y se ejecutan acciones:

- **Aprobar**: cambia a `approved`, crea usuario portal, genera enlace signup/reset y notifica por WhatsApp.
- **Rechazar**: cambia a `rejected` y notifica por WhatsApp.

## Portal y red social

### `/my/tourism/profile`

Usuario autenticado puede:

- Editar nombre, móvil, WhatsApp, descripción y portada.
- Ver sus publicaciones.
- Crear publicaciones.
- Editar o borrar sus propias publicaciones.

### `/tourism/feed`

Feed público estilo red social con cards Bootstrap que muestra:

- Nombre del prestador.
- Foto de perfil (`image_1920`).
- Portada (`cover_image`) si existe.
- Contenido e imagen del post.
- Fecha de publicación.

## Pruebas manuales sugeridas

1. Configurar parámetros de Meta API.
2. Verificar webhook con Meta (`GET /whatsapp/webhook`).
3. Enviar mensaje WhatsApp y completar flujo (nombre + foto).
4. Confirmar partner creado con `pending`.
5. Aprobar desde CRM y validar creación de usuario portal.
6. Abrir link recibido por WhatsApp y definir contraseña.
7. Iniciar sesión y editar perfil en `/my/tourism/profile`.
8. Crear/editar/borrar posts propios.
9. Revisar `/tourism/feed` con publicaciones aprobadas.

## Notas técnicas

- `whatsapp_number` tiene unicidad SQL.
- Usuario portal **solo** se crea al aprobar.
- Reglas de seguridad limitan portal a su propio perfil y sus propios posts.
- La foto principal del perfil siempre usa `image_1920`.

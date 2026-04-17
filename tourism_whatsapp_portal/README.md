# tourism_whatsapp_portal

Módulo Odoo 18 para onboarding de prestadores turísticos con **registro inicial 100% por WhatsApp**.

## Regla estricta de negocio

Este módulo **prohíbe** el registro web inicial con correo + contraseña.

- ❌ No hay formulario de alta web para crear cuentas desde cero.
- ✅ El alta inicial ocurre solo mediante chatbot de WhatsApp (Meta Cloud API).
- ✅ El acceso web se habilita únicamente después de la aprobación del comité.

## Flujo funcional implementado

### Fase 1: Registro 100% WhatsApp

1. Meta llama al webhook `/whatsapp/webhook`.
2. Si el número no existe, se crea `res.partner` con:
   - `is_tourism_provider=True`
   - `whatsapp_number=<from>`
   - `chatbot_state='start'`
   - `tourism_approval_state='draft'`
3. Máquina de estados:
   - `start` → bot pide nombre y pasa a `asking_name`.
   - `asking_name` → guarda texto en `name`, pide foto y pasa a `asking_photo`.
   - `asking_photo` → descarga imagen desde Graph API, guarda en `image_1920`, pasa a `completed` y `tourism_approval_state='pending'`.
4. El bot responde: **"Perfil completado. En revisión por el comité."**

### Fase 2: Aprobación del comité (backend)

1. Menú de backend con vista tree/form filtrada por `tourism_approval_state='pending'`.
2. Botón **Aprobar Prestador** (`action_approve_provider`) en `res.partner`:
   - cambia estado a `approved`
   - crea (o reutiliza) usuario `res.users` portal vinculado al partner
   - genera enlace de creación/restablecimiento de contraseña usando `auth_signup`
   - envía WhatsApp: **"¡Felicidades! Fuiste aprobado... [ENLACE]"**

### Fase 3: Red social turística (portal)

1. Modelo `tourism.post` con:
   - `content`
   - `image`
   - `author_id` (`res.partner`)
2. Portal:
   - `/my/tourism/profile`: edición de datos y `cover_image` del usuario logueado.
   - `/tourism/feed`: feed de publicaciones con estilo tarjetas Bootstrap y formulario rápido para postear si el usuario está logueado.

## Configuración requerida

En **Ajustes** (parámetros del sistema), definir:

- `tourism_whatsapp_portal.verify_token`
- `tourism_whatsapp_portal.access_token`
- `tourism_whatsapp_portal.phone_number_id`

## Nota técnica

El módulo usa rutas con sintaxis moderna de Odoo 18 (`request.env`) y webhook con `csrf=False`.

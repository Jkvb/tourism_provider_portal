# tourism_provider_portal

Módulo Odoo para registro, validación y publicación de prestadores turísticos municipales.

## Cambio funcional: registro y actualización por chatbot de WhatsApp

A partir de esta versión, **todo el alta y actualización de prestadores se hace por chatbot de WhatsApp**.

- La ruta `/turismo/registro` ya no muestra formulario web; ahora redirige al flujo conversacional de WhatsApp.
- En portal (`/my/turismo/prestadores`) las acciones de edición se canalizan por WhatsApp.
- En el detalle público del prestador se agrega acceso directo para solicitar actualización por chatbot.

## Configurar el chatbot de WhatsApp

El módulo construye enlaces `https://wa.me/...` con un mensaje inicial según el flujo (registro o actualización). Para configurarlo:

### 1) Activar modo desarrollador en Odoo

1. Ir a **Ajustes**.
2. En tu usuario, habilitar **Modo desarrollador**.

### 2) Definir número del chatbot (obligatorio)

1. Ir a **Ajustes → Técnico → Parámetros del sistema**.
2. Crear/editar el parámetro:
   - **Clave:** `tourism_provider_portal.whatsapp_bot_phone`
   - **Valor:** número en formato internacional (ejemplo México): `5213312345678`

> Recomendación: usa solo dígitos (sin `+`, espacios ni guiones). Si agregas caracteres, el módulo intentará limpiarlos automáticamente.

### 3) Definir nombre del municipio para el mensaje inicial (opcional)

1. En **Parámetros del sistema**, crear/editar:
   - **Clave:** `tourism_provider_portal.chatbot_municipality_name`
   - **Valor:** nombre a mostrar en el saludo (ejemplo: `Atemajac de Brizuela`)

Si este parámetro no existe, el módulo usa `Atemajac de Brizuela` por defecto.

## Prueba rápida de funcionamiento

1. Abrir `/turismo/registro`.
2. Presionar **Iniciar registro por WhatsApp**.
3. Verificar que abre conversación hacia el número configurado y con texto precargado.
4. Entrar a `/my/turismo/prestadores` y usar **Actualizar por WhatsApp** en un prestador.

## Integración sugerida del bot

Para operación real, conecta tu número de WhatsApp Business API con un bot (por ejemplo, Twilio + webhook, Meta Cloud API o proveedor BSP). El bot debería:

1. Identificar intención (`REGISTRO` vs `ACTUALIZACIÓN`).
2. Solicitar datos paso a paso (negocio, responsable, contacto, categoría, ubicación, servicios, medios).
3. Recibir imágenes/documentos.
4. Enviar la información a Odoo vía endpoint interno/API segura para crear o actualizar `tourism.provider`.
5. Confirmar folio al usuario y notificar al equipo revisor.

## Notas

- Si no configuras `tourism_provider_portal.whatsapp_bot_phone`, el sistema abrirá `wa.me` sin número fijo.
- El flujo de publicaciones (`novedades`) en perfil público se mantiene vía portal web.

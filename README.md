# tourism_provider_portal

Módulo Odoo para registro, validación y publicación de prestadores turísticos municipales.

## Flujo ultra simple de registro

Ahora el alta es mínima:

1. Iniciar sesión en Odoo (puede ser con Google/Facebook si esos proveedores están configurados en tu login de Odoo).
2. Entrar a `/turismo/registro`.
3. Escribir únicamente **por qué quieres una cuenta**.
4. Enviar solicitud.

No se piden más datos durante el registro inicial.

## Aprobación antes de editar/publicar

Después de solicitar cuenta, el perfil queda en `pending` y:

- **No** puede editar portada/foto de perfil.
- **No** puede crear publicaciones.

Cuando un validador aprueba la cuenta, entonces se habilita el panel frontend para:

- Foto de perfil
- Foto de portada
- Edición de perfil
- Publicaciones (texto + imagen)

## Notas técnicas

- La solicitud toma automáticamente el nombre/correo/teléfono del usuario autenticado.
- Se asigna por defecto la primera categoría activa disponible.
- Se añadió corrección de esquema para `tourism.provider.post.body` con `NOT NULL`.

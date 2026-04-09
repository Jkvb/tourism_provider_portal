# tourism_provider_portal

Módulo Odoo para registro, validación y publicación de prestadores turísticos municipales.

## Flujo simplificado solicitado

Se simplificó el proceso para que el registro sea rápido desde frontend:

1. **Nombre del perfil**
2. **Número de contacto**
3. **Correo**
4. **Descripción de la petición**

Con eso se crea un registro en estado **pendiente de revisión**.

## ¿Qué pasa después del registro?

Una vez registrado (y con sesión iniciada), el usuario tiene un panel frontend tipo red social en:

- `/my/turismo/prestadores`
- `/my/turismo/prestador/<id>`

En ese panel puede:

- Subir **foto de perfil**.
- Subir **foto de portada**.
- Editar datos básicos del perfil.
- Crear publicaciones (texto + imagen) de forma rápida.

## Comportamiento funcional

- Se eliminó la dependencia del flujo por WhatsApp chatbot.
- El alta rápida usa categoría por defecto (la primera categoría activa disponible).
- Las modificaciones del perfil se vuelven a enviar a revisión (`pending`) para control administrativo.
- Las publicaciones se crean desde frontend del prestador autenticado.

## Prueba rápida

1. Abrir `/turismo/registro` y completar los 4 campos.
2. Iniciar sesión con el usuario vinculado al prestador.
3. Ir a `/my/turismo/prestadores` y abrir el perfil.
4. Subir portada/foto de perfil y crear una publicación.

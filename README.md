# tourism_provider_portal

Módulo Odoo 18 para gestionar prestadores turísticos con experiencia **web-first**.

> Sí: **el módulo principal ya incluye el flujo web + WhatsApp**.  
> El módulo interno `whatsapp_turismo_bot/` es una variante separada/legacy y **no se recomienda instalarlo junto con `tourism_provider_portal`** porque ambos extienden `res.partner` con campos del mismo nombre.

## ¿Qué módulo instalo?

### Opción recomendada (producción)
Instala **solo** `tourism_provider_portal`.

### Opción alternativa (solo pruebas aisladas)
Instala `whatsapp_turismo_bot` **en otra base de datos**, si quieres probar únicamente ese bot minimalista.

---

## Instalación paso a paso

1. Copia este repositorio a tu ruta de addons (por ejemplo `/mnt/extra-addons`).
2. En Odoo, actualiza lista de apps.
3. Instala el módulo **Tourism Provider Portal** (`tourism_provider_portal`).
4. (Opcional) Configura WhatsApp en:
   - **Ajustes → WhatsApp Turismo Bot**
   - Captura:
     - `WhatsApp Verify Token`
     - `WhatsApp Access Token`
     - `WhatsApp Phone Number ID`
5. Configura en Meta la URL del webhook:
   - `https://<tu-dominio>/whatsapp/webhook`

## Flujo implementado

1. **Registro ultra simple** en `/turismo/registro` (solo correo + confirmar correo).
2. Se crea usuario portal inactivo + perfil mínimo `tourism.provider` en estado `incomplete`.
3. Se envía correo de confirmación con token único.
4. Confirmación en `/turismo/confirmar/<token>` activa la cuenta y dispara email de seteo de contraseña.
5. El prestador entra a `/my/turismo/perfil` para completar onboarding frontend.
6. Puede enviar a revisión cuando el perfil esté completo.
7. Admin/validador aprueban y publican.
8. Perfil público visual en `/turismo/prestador/<slug>` con portada, avatar y feed de posts.

## Estados recomendados

- `incomplete`: cuenta creada, perfil incompleto.
- `pending`: listo para revisión.
- `approved`: aprobado internamente.
- `published`: visible públicamente.
- `rejected` / `unpublished`: control editorial.

## Seguridad

- Portal solo puede editar su propio perfil.
- Portal solo puede crear/editar/eliminar sus propios posts.
- Público solo ve perfiles publicados.
- Público solo ve posts publicados de perfiles publicados.

## Actualización del módulo

```bash
odoo -d <db> -u tourism_provider_portal --stop-after-init
```

## Notas de migración

- Se agregaron campos de confirmación de correo: `signup_email`, `email_confirmed`, `confirmation_token`, `confirmation_sent_date`, `confirmation_date`.
- `name`, `responsible_name` y `category_id` en `tourism.provider` dejaron de ser obligatorios al crear registro mínimo.
- Nuevo estado `incomplete`.
- Se agregó dependencia `auth_signup` para flujo de activación/reset password.

# tourism_provider_portal

Módulo Odoo 19 para gestionar prestadores turísticos con experiencia **web-first**.

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

## Limpieza de canales externos

El módulo quedó 100% centrado en la experiencia web del portal.

## Actualización del módulo

```bash
odoo -d <db> -u tourism_provider_portal --stop-after-init
```

## Notas de migración

- Se agregaron campos de confirmación de correo: `signup_email`, `email_confirmed`, `confirmation_token`, `confirmation_sent_date`, `confirmation_date`.
- `name`, `responsible_name` y `category_id` en `tourism.provider` dejaron de ser obligatorios al crear registro mínimo.
- Nuevo estado `incomplete`.
- Se agregó dependencia `auth_signup` para flujo de activación/reset password.

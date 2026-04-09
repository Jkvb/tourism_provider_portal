import base64
from urllib.parse import quote

from odoo import _, http
from odoo.http import request


class TourismPortalController(http.Controller):
    def _provider_base_domain(self):
        return [("state", "=", "published"), ("is_published", "=", True)]

    def _default_category_id(self):
        category = request.env["tourism.provider.category"].sudo().search([("active", "=", True)], limit=1)
        if not category:
            category = request.env["tourism.provider.category"].sudo().search([], limit=1)
        return category.id if category else False

    @http.route(["/turismo", "/turismo/prestadores"], type="http", auth="public", website=True, sitemap=True)
    def tourism_home(self, category_id=None, search=None, **kwargs):
        category_id = int(category_id) if category_id and str(category_id).isdigit() else False
        domain = self._provider_base_domain()
        if category_id:
            domain.append(("category_id", "=", category_id))
        if search:
            domain.append(("name", "ilike", search))

        providers = request.env["tourism.provider"].sudo().search(domain, limit=60)
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        featured = request.env["tourism.provider"].sudo().search(self._provider_base_domain(), limit=6)
        values = {
            "providers": providers,
            "categories": categories,
            "featured_providers": featured,
            "selected_category": category_id,
            "search": search or "",
            "register_url": "/turismo/registro",
            "whatsapp_register_url": self._build_whatsapp_chatbot_url(self._chatbot_message("register")),
        }
        return request.render("tourism_provider_portal.tourism_home", values)

    @http.route("/turismo/prestador/<string:slug>", type="http", auth="public", website=True, sitemap=True)
    def tourism_provider_detail(self, slug, **kwargs):
        provider = (
            request.env["tourism.provider"]
            .sudo()
            .search(self._provider_base_domain() + [("website_slug", "=", slug)], limit=1)
        )
        if not provider:
            return request.not_found()
        can_publish_post = not request.env.user._is_public() and provider.portal_user_id.id == request.env.user.id
        return request.render(
            "tourism_provider_portal.tourism_provider_detail",
            {
                "provider": provider,
                "register_url": "/turismo/registro",
                "can_publish_post": can_publish_post,
                "whatsapp_update_url": self._build_whatsapp_chatbot_url(
                    self._chatbot_message("update", provider=provider)
                ),
            },
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["GET"])
    def tourism_register(self, **kwargs):
        return request.render(
            "tourism_provider_portal.tourism_provider_register",
            {
                "form_values": kwargs,
                "error": False,
                "success": False,
                "register_url": "/turismo/registro",
                "needs_login": request.env.user._is_public(),
            },
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def tourism_register_submit(self, **post):
        if request.env.user._is_public():
            return request.redirect("/web/login?redirect=/turismo/registro")

        reason = (post.get("description") or "").strip()
        category_id = self._default_category_id()
        if not reason or not category_id:
            return request.render(
                "tourism_provider_portal.tourism_provider_register",
                {
                    "form_values": post,
                    "error": "Solo necesitamos que nos cuentes por qué quieres una cuenta.",
                    "success": False,
                    "register_url": "/turismo/registro",
                    "needs_login": False,
                },
            )

        user = request.env.user
        vals = {
            "name": user.name,
            "responsible_name": user.name,
            "category_id": category_id,
            "description": reason,
            "services_description": reason,
            "phone": user.partner_id.phone or user.partner_id.mobile,
            "email": user.partner_id.email,
            "state": "pending",
            "is_published": False,
            "terms_accepted": True,
            "portal_user_id": user.id,
        }

        provider = request.env["tourism.provider"].sudo().create(vals)
        provider.message_post(body="Solicitud rápida creada desde /turismo/registro")

        validators = request.env.ref("tourism_provider_portal.group_tourism_validator").users
        admins = request.env.ref("tourism_provider_portal.group_tourism_admin").users
        users_to_notify = (validators | admins).filtered(lambda u: u.partner_id)
        if users_to_notify:
            provider.message_subscribe(partner_ids=users_to_notify.mapped("partner_id").ids)
            provider.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=users_to_notify[0].id,
                summary="Nueva solicitud rápida de prestador",
                note=f"Se registró '{provider.name}' y está pendiente de revisión.",
            )

        return request.render(
            "tourism_provider_portal.tourism_provider_register",
            {
                "form_values": {},
                "error": False,
                "success": "Solicitud enviada. Cuando tu cuenta sea aprobada podrás editar perfil y publicar.",
                "register_url": "/turismo/registro",
                "needs_login": False,
            },
        )

    @http.route("/my/turismo/prestadores", type="http", auth="user", website=True)
    def my_tourism_providers(self, **kwargs):
        providers = request.env["tourism.provider"].sudo().search([("portal_user_id", "=", request.env.user.id)])
        return request.render(
            "tourism_provider_portal.tourism_portal_my_providers",
            {
                "providers": providers,
                "whatsapp_register_url": self._build_whatsapp_chatbot_url(self._chatbot_message("register")),
            },
        )

    @http.route(["/my/turismo/prestador/<int:provider_id>"], type="http", auth="user", website=True, methods=["GET"])
    def my_tourism_provider_form(self, provider_id, **kwargs):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        can_manage_profile = provider.state in ("approved", "published")
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {
                "provider": provider,
                "categories": categories,
                "error": False,
                "success": False,
                "can_manage_profile": can_manage_profile,
            },
        )

    @http.route(["/my/turismo/prestador/<int:provider_id>"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_submit(self, provider_id, **post):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()

        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        if provider.state not in ("approved", "published"):
            return request.render(
                "tourism_provider_portal.tourism_portal_provider_edit",
                {
                    "provider": provider,
                    "categories": categories,
                    "error": "Tu cuenta aún no está aprobada. No puedes editar perfil todavía.",
                    "success": False,
                    "can_manage_profile": False,
                },
            )

        vals = {
            "name": post.get("name"),
            "responsible_name": post.get("name") or provider.responsible_name,
            "phone": post.get("phone"),
            "email": post.get("email"),
            "description": post.get("description"),
            "category_id": int(post.get("category_id")) if post.get("category_id") else provider.category_id.id,
            "state": "pending",
            "is_published": False,
        }
        profile_image = post.get("profile_image_1920")
        if profile_image and getattr(profile_image, "filename", False):
            vals["profile_image_1920"] = base64.b64encode(profile_image.read())

        cover_image = post.get("cover_image_1920")
        if cover_image and getattr(cover_image, "filename", False):
            vals["cover_image_1920"] = base64.b64encode(cover_image.read())

        provider.write(vals)
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {
                "provider": provider,
                "categories": categories,
                "error": False,
                "success": "Perfil actualizado. Tus cambios se enviaron a revisión.",
                "can_manage_profile": False,
            },
        )

    @http.route(["/my/turismo/prestador/<int:provider_id>/post"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_post_create(self, provider_id, **post):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()

        if provider.state not in ("approved", "published"):
            return request.redirect(f"/my/turismo/prestador/{provider.id}")

        body = (post.get("body") or "").strip()
        if not body:
            return request.redirect(f"/my/turismo/prestador/{provider.id}")

        vals = {
            "provider_id": provider.id,
            "author_user_id": request.env.user.id,
            "body": body,
            "is_published": True,
        }
        post_image = post.get("post_image")
        if post_image and getattr(post_image, "filename", False):
            vals["image_1920"] = base64.b64encode(post_image.read())

        request.env["tourism.provider.post"].sudo().create(vals)
        return request.redirect(f"/my/turismo/prestador/{provider.id}")

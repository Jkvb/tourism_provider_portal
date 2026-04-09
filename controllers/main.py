import base64
from urllib.parse import quote

from odoo import _, http
from odoo.http import request


class TourismPortalController(http.Controller):
    def _provider_base_domain(self):
        return [("state", "=", "published"), ("is_published", "=", True)]

    def _get_whatsapp_bot_phone(self):
        phone = request.env["ir.config_parameter"].sudo().get_param(
            "tourism_provider_portal.whatsapp_bot_phone", default=""
        )
        return "".join(ch for ch in phone if ch.isdigit())

    def _build_whatsapp_chatbot_url(self, message):
        phone = self._get_whatsapp_bot_phone()
        encoded = quote(message or "")
        if phone:
            return f"https://wa.me/{phone}?text={encoded}"
        return f"https://wa.me/?text={encoded}"

    def _chatbot_message(self, action, provider=None):
        municipality = (
            request.env["ir.config_parameter"].sudo().get_param(
                "tourism_provider_portal.chatbot_municipality_name", default="Atemajac de Brizuela"
            )
        )
        if action == "register":
            return _(
                "Hola, quiero REGISTRAR un prestador turístico en %(municipality)s. "
                "Compárteme el flujo del chatbot para iniciar."
            ) % {"municipality": municipality}
        if action == "update" and provider:
            return _(
                "Hola, quiero ACTUALIZAR mi registro turístico. "
                "Prestador: %(provider)s (ID: %(provider_id)s)."
            ) % {"provider": provider.name, "provider_id": provider.id}
        return _("Hola, necesito ayuda con el registro turístico.")

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
        can_publish_post = (
            not request.env.user._is_public()
            and provider.portal_user_id.id == request.env.user.id
            and provider.state == "published"
        )
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
                "whatsapp_url": self._build_whatsapp_chatbot_url(self._chatbot_message("register")),
                "register_url": "/turismo/registro",
            },
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def tourism_register_submit(self, **post):
        return request.redirect(self._build_whatsapp_chatbot_url(self._chatbot_message("register")))

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
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {
                "provider": provider,
                "whatsapp_url": self._build_whatsapp_chatbot_url(self._chatbot_message("update", provider=provider)),
            },
        )

    @http.route(["/my/turismo/prestador/<int:provider_id>"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_submit(self, provider_id, **post):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()
        return request.redirect(self._build_whatsapp_chatbot_url(self._chatbot_message("update", provider=provider)))

    @http.route(["/my/turismo/prestador/<int:provider_id>/post"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_post_create(self, provider_id, **post):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()

        body = (post.get("body") or "").strip()
        if not body:
            return request.redirect(f"/turismo/prestador/{provider.website_slug}")

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
        return request.redirect(f"/turismo/prestador/{provider.website_slug}")

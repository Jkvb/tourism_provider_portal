import base64

from odoo import http
from odoo.http import request


class TourismPortalController(http.Controller):
    def _provider_base_domain(self):
        return [("state", "=", "published"), ("is_published", "=", True)]

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
        return request.render(
            "tourism_provider_portal.tourism_provider_detail",
            {"provider": provider, "register_url": "/turismo/registro"},
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["GET"])
    def tourism_register(self, **kwargs):
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        states = request.env["res.country.state"].sudo().search([("country_id.code", "=", "MX")])
        return request.render(
            "tourism_provider_portal.tourism_provider_register",
            {
                "categories": categories,
                "states": states,
                "form_values": kwargs,
                "error": False,
                "success": False,
                "register_url": "/turismo/registro",
            },
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def tourism_register_submit(self, **post):
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        states = request.env["res.country.state"].sudo().search([("country_id.code", "=", "MX")])

        required_fields = ["name", "responsible_name", "category_id", "email", "city"]
        missing = [field for field in required_fields if not post.get(field)]
        if missing or not post.get("terms_accepted"):
            return request.render(
                "tourism_provider_portal.tourism_provider_register",
                {
                    "categories": categories,
                    "states": states,
                    "form_values": post,
                    "error": "Completa los campos obligatorios y acepta términos.",
                    "success": False,
                    "register_url": "/turismo/registro",
                },
            )

        vals = {
            "name": post.get("name"),
            "responsible_name": post.get("responsible_name"),
            "category_id": int(post.get("category_id")),
            "description": post.get("description"),
            "phone": post.get("phone"),
            "whatsapp": post.get("whatsapp"),
            "email": post.get("email"),
            "street": post.get("street"),
            "location_reference": post.get("location_reference"),
            "city": post.get("city"),
            "state_id": int(post.get("state_id")) if post.get("state_id") else False,
            "facebook_url": post.get("facebook_url"),
            "instagram_url": post.get("instagram_url"),
            "tiktok_url": post.get("tiktok_url"),
            "website_url": post.get("website_url"),
            "schedule": post.get("schedule"),
            "services_description": post.get("services_description"),
            "terms_accepted": True,
            "state": "pending",
            "portal_user_id": request.env.user.id if request.env.user and not request.env.user._is_public() else False,
        }

        main_image = post.get("image_1920")
        if main_image and getattr(main_image, "filename", False):
            vals["image_1920"] = base64.b64encode(main_image.read())

        provider = request.env["tourism.provider"].sudo().create(vals)

        gallery_commands = []
        for key in sorted(post):
            if key.startswith("gallery_"):
                file_obj = post[key]
                if getattr(file_obj, "filename", False):
                    gallery_commands.append(
                        (
                            0,
                            0,
                            {
                                "name": file_obj.filename,
                                "image_1920": base64.b64encode(file_obj.read()),
                            },
                        )
                    )
        if gallery_commands:
            provider.sudo().write({"gallery_image_ids": gallery_commands})

        provider.message_post(body="Solicitud creada desde formulario público /turismo/registro")

        validators = request.env.ref("tourism_provider_portal.group_tourism_validator").users
        admins = request.env.ref("tourism_provider_portal.group_tourism_admin").users
        users_to_notify = (validators | admins).filtered(lambda u: u.partner_id)
        if users_to_notify:
            provider.message_subscribe(partner_ids=users_to_notify.mapped("partner_id").ids)
            provider.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=users_to_notify[0].id,
                summary="Nueva solicitud de prestador turístico",
                note=f"Se registró '{provider.name}' y está pendiente de revisión.",
            )

        return request.render(
            "tourism_provider_portal.tourism_provider_register",
            {
                "categories": categories,
                "states": states,
                "form_values": {},
                "error": False,
                "success": "Tu solicitud fue enviada y está en revisión.",
                "register_url": "/turismo/registro",
            },
        )

    @http.route("/my/turismo/prestadores", type="http", auth="user", website=True)
    def my_tourism_providers(self, **kwargs):
        providers = request.env["tourism.provider"].sudo().search([("portal_user_id", "=", request.env.user.id)])
        return request.render(
            "tourism_provider_portal.tourism_portal_my_providers",
            {"providers": providers},
        )

    @http.route(["/my/turismo/prestador/<int:provider_id>"], type="http", auth="user", website=True, methods=["GET"])
    def my_tourism_provider_form(self, provider_id, **kwargs):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {"provider": provider, "categories": categories, "error": False, "success": False},
        )

    @http.route(["/my/turismo/prestador/<int:provider_id>"], type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_submit(self, provider_id, **post):
        provider = request.env["tourism.provider"].sudo().browse(provider_id)
        if not provider.exists() or provider.portal_user_id.id != request.env.user.id:
            return request.not_found()
        vals = {
            "name": post.get("name"),
            "responsible_name": post.get("responsible_name"),
            "phone": post.get("phone"),
            "whatsapp": post.get("whatsapp"),
            "email": post.get("email"),
            "street": post.get("street"),
            "location_reference": post.get("location_reference"),
            "description": post.get("description"),
            "schedule": post.get("schedule"),
            "services_description": post.get("services_description"),
            "category_id": int(post.get("category_id")) if post.get("category_id") else provider.category_id.id,
            "state": "pending",
            "is_published": False,
        }
        provider.write(vals)
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {
                "provider": provider,
                "categories": categories,
                "error": False,
                "success": "Cambios guardados y reenviados a revisión.",
            },
        )

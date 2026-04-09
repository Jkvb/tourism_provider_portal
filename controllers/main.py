import base64
import re

from odoo import _, fields, http
from odoo.http import request

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class TourismPortalController(http.Controller):
    def _provider_base_domain(self):
        return [("state", "=", "published"), ("is_published", "=", True)]

    def _default_category(self):
        category = request.env["tourism.provider.category"].sudo().search([("active", "=", True)], limit=1)
        if not category:
            category = request.env["tourism.provider.category"].sudo().search([], limit=1)
        return category

    def _current_provider(self):
        return request.env["tourism.provider"].sudo().search([("portal_user_id", "=", request.env.user.id)], limit=1)

    @http.route(["/turismo", "/turismo/prestadores"], type="http", auth="public", website=True, sitemap=True)
    def tourism_home(self, category_id=None, search=None, **kwargs):
        category_id = int(category_id) if category_id and str(category_id).isdigit() else False
        domain = self._provider_base_domain()
        if category_id:
            domain.append(("category_id", "=", category_id))
        if search:
            domain += ["|", ("name", "ilike", search), ("description", "ilike", search)]

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

        posts = provider.post_ids.filtered(lambda p: p.is_published)
        return request.render(
            "tourism_provider_portal.tourism_provider_detail",
            {
                "provider": provider,
                "posts": posts,
            },
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["GET"])
    def tourism_register(self, **kwargs):
        return request.render(
            "tourism_provider_portal.tourism_provider_register_webfirst",
            {
                "form_values": kwargs,
                "error": False,
                "success": False,
            },
        )

    @http.route("/turismo/registro", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def tourism_register_submit(self, **post):
        email = (post.get("email") or "").strip().lower()
        email_confirm = (post.get("email_confirm") or "").strip().lower()

        if not email or not email_confirm:
            if post.get("description"):
                error = _("La pantalla de registro está desactualizada. Recarga la página y captura correo + confirmar correo.")
            else:
                error = _("Debes capturar y confirmar tu correo.")
        elif not EMAIL_RE.match(email):
            error = _("El correo no tiene un formato válido.")
        elif email != email_confirm:
            error = _("Los correos no coinciden.")
        else:
            error = False

        if not error:
            provider_exists = request.env["tourism.provider"].sudo().search_count([("signup_email", "=", email)])
            user_exists = request.env["res.users"].sudo().search_count([("login", "=", email)])
            if provider_exists or user_exists:
                error = _("Ese correo ya está registrado. Inicia sesión o recupera tu contraseña.")

        if error:
            return request.render(
                "tourism_provider_portal.tourism_provider_register_webfirst",
                {
                    "form_values": post,
                    "error": error,
                    "success": False,
                },
            )

        portal_group = request.env.ref("base.group_portal")
        user = (
            request.env["res.users"]
            .sudo()
            .with_context(no_reset_password=True)
            .create(
                {
                    "name": email,
                    "login": email,
                    "email": email,
                    "active": False,
                    "groups_id": [(6, 0, [portal_group.id])],
                }
            )
        )

        provider = request.env["tourism.provider"].sudo().create(
            {
                "name": email.split("@")[0],
                "responsible_name": email.split("@")[0],
                "portal_user_id": user.id,
                "signup_email": email,
                "email": email,
                "category_id": self._default_category().id,
                "state": "incomplete",
                "is_published": False,
            }
        )
        provider.regenerate_confirmation_token()
        provider.action_send_confirmation_email()

        return request.render(
            "tourism_provider_portal.tourism_register_success",
            {"email": email},
        )

    @http.route("/turismo/confirmar/<string:token>", type="http", auth="public", website=True)
    def tourism_confirm_email(self, token, **kwargs):
        provider = request.env["tourism.provider"].sudo().search([("confirmation_token", "=", token)], limit=1)
        if not provider:
            return request.render("tourism_provider_portal.tourism_confirm_error")

        provider.write(
            {
                "email_confirmed": True,
                "confirmation_date": fields.Datetime.now(),
                "confirmation_token": False,
            }
        )
        provider.portal_user_id.sudo().write({"active": True})
        provider.portal_user_id.sudo().action_reset_password()
        return request.render("tourism_provider_portal.tourism_confirm_success")

    @http.route("/my/turismo/perfil", type="http", auth="user", website=True, methods=["GET"])
    def my_tourism_profile(self, **kwargs):
        provider = self._current_provider()
        if not provider:
            return request.redirect("/turismo/registro")
        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {
                "provider": provider,
                "categories": categories,
                "error": False,
                "success": False,
                "posts": provider.post_ids,
            },
        )

    @http.route("/my/turismo/perfil", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_profile_submit(self, **post):
        provider = self._current_provider()
        if not provider:
            return request.redirect("/turismo/registro")

        vals = {
            "name": (post.get("name") or "").strip(),
            "responsible_name": (post.get("responsible_name") or "").strip(),
            "phone": (post.get("phone") or "").strip(),
            "email": (post.get("email") or "").strip(),
            "description": post.get("description"),
            "category_id": int(post.get("category_id")) if post.get("category_id") else False,
            "street": (post.get("street") or "").strip(),
            "location_reference": (post.get("location_reference") or "").strip(),
            "city": (post.get("city") or "").strip(),
            "schedule": (post.get("schedule") or "").strip(),
            "services_description": (post.get("services_description") or "").strip(),
            "facebook_url": (post.get("facebook_url") or "").strip(),
            "instagram_url": (post.get("instagram_url") or "").strip(),
            "tiktok_url": (post.get("tiktok_url") or "").strip(),
            "website_url": (post.get("website_url") or "").strip(),
            "state": "incomplete" if provider.state in ("draft", "incomplete", "rejected") else provider.state,
            "is_published": False if provider.state in ("published", "approved") else provider.is_published,
        }

        profile_image = post.get("profile_image_1920")
        if profile_image and getattr(profile_image, "filename", False):
            vals["profile_image_1920"] = base64.b64encode(profile_image.read())

        cover_image = post.get("cover_image_1920")
        if cover_image and getattr(cover_image, "filename", False):
            vals["cover_image_1920"] = base64.b64encode(cover_image.read())

        provider.sudo().write(vals)

        categories = request.env["tourism.provider.category"].sudo().search([("active", "=", True)])
        return request.render(
            "tourism_provider_portal.tourism_portal_provider_edit",
            {
                "provider": provider,
                "categories": categories,
                "error": False,
                "success": _("Perfil guardado. Puedes enviarlo a revisión cuando esté completo."),
                "posts": provider.post_ids,
            },
        )

    @http.route("/my/turismo/perfil/enviar_revision", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_submit_review(self, **post):
        provider = self._current_provider()
        if not provider:
            return request.redirect("/turismo/registro")
        provider.sudo().action_submit_for_review()
        return request.redirect("/my/turismo/perfil")

    @http.route("/my/turismo/post/create", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_post_create(self, **post):
        provider = self._current_provider()
        if not provider:
            return request.redirect("/turismo/registro")

        body = (post.get("body") or "").strip()
        if not body:
            return request.redirect("/my/turismo/perfil")

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
        return request.redirect("/my/turismo/perfil")

    @http.route("/my/turismo/post/<int:post_id>/edit", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_post_edit(self, post_id, **post):
        post_record = request.env["tourism.provider.post"].sudo().browse(post_id)
        provider = self._current_provider()
        if not post_record.exists() or not provider or post_record.provider_id.id != provider.id:
            return request.not_found()

        vals = {"body": (post.get("body") or "").strip()}
        post_image = post.get("post_image")
        if post_image and getattr(post_image, "filename", False):
            vals["image_1920"] = base64.b64encode(post_image.read())
        post_record.sudo().write(vals)
        return request.redirect("/my/turismo/perfil")

    @http.route("/my/turismo/post/<int:post_id>/delete", type="http", auth="user", website=True, methods=["POST"], csrf=True)
    def my_tourism_provider_post_delete(self, post_id, **post):
        post_record = request.env["tourism.provider.post"].sudo().browse(post_id)
        provider = self._current_provider()
        if not post_record.exists() or not provider or post_record.provider_id.id != provider.id:
            return request.not_found()
        post_record.sudo().unlink()
        return request.redirect("/my/turismo/perfil")

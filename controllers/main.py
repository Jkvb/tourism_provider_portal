import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TourismProviderPortalController(http.Controller):
    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["GET"], csrf=False)
    def whatsapp_webhook_verify(self, **kwargs):
        mode = kwargs.get("hub.mode")
        verify_token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")

        expected = request.env["ir.config_parameter"].sudo().get_param(
            "tourism_provider_portal.verify_token"
        )
        if mode == "subscribe" and verify_token and verify_token == expected and challenge:
            return request.make_response(challenge, headers=[("Content-Type", "text/plain")])
        return request.make_response("Verification failed", status=403)

    @http.route("/whatsapp/webhook", type="json", auth="public", methods=["POST"], csrf=False)
    def whatsapp_webhook_receive(self, **kwargs):
        payload = request.jsonrequest or {}
        self._process_whatsapp_payload(payload)
        return {"status": "ok"}

    @http.route("/my/tourism/profile", type="http", auth="user", website=True)
    def my_tourism_profile(self, **kwargs):
        user = request.env.user
        partner = user.partner_id.sudo()
        posts = (
            request.env["tourism.post"]
            .sudo()
            .search([("author_id", "=", partner.id)], order="create_date desc")
        )
        values = {
            "partner": partner,
            "posts": posts,
        }
        return request.render("tourism_provider_portal.my_tourism_profile", values)

    @http.route("/my/tourism/profile/save", type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def save_tourism_profile(self, **post):
        partner = request.env.user.partner_id.sudo()
        vals = {
            "name": post.get("name") or partner.name,
            "phone": post.get("phone"),
            "whatsapp_number": post.get("whatsapp_number") or partner.whatsapp_number,
            "website_description": post.get("website_description"),
        }
        cover_file = request.httprequest.files.get("cover_image")
        if cover_file:
            vals["cover_image"] = cover_file.read()
        partner.write(vals)
        return request.redirect("/my/tourism/profile")

    @http.route("/my/tourism/post/create", type="http", auth="user", methods=["POST"], website=True, csrf=True)
    def create_tourism_post(self, **post):
        content = (post.get("content") or "").strip()
        if not content:
            return request.redirect("/my/tourism/profile")

        vals = {
            "content": content,
            "author_id": request.env.user.partner_id.id,
            "is_published": True,
        }
        image_file = request.httprequest.files.get("image")
        if image_file:
            vals["image"] = image_file.read()

        request.env["tourism.post"].sudo().create(vals)
        return request.redirect("/my/tourism/profile")

    @http.route(
        "/my/tourism/post/<int:post_id>/edit",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def edit_tourism_post(self, post_id, **post):
        record = request.env["tourism.post"].sudo().browse(post_id)
        if not record.exists() or (
            record.author_id != request.env.user.partner_id
            and not request.env.user.has_group("base.group_system")
        ):
            return request.redirect("/my/tourism/profile")

        vals = {"content": (post.get("content") or record.content).strip()}
        image_file = request.httprequest.files.get("image")
        if image_file:
            vals["image"] = image_file.read()
        record.write(vals)
        return request.redirect("/my/tourism/profile")

    @http.route(
        "/my/tourism/post/<int:post_id>/delete",
        type="http",
        auth="user",
        methods=["POST"],
        website=True,
        csrf=True,
    )
    def delete_tourism_post(self, post_id, **kwargs):
        record = request.env["tourism.post"].sudo().browse(post_id)
        if record.exists() and (
            record.author_id == request.env.user.partner_id
            or request.env.user.has_group("base.group_system")
        ):
            record.unlink()
        return request.redirect("/my/tourism/profile")

    @http.route("/tourism/feed", type="http", auth="public", website=True)
    def tourism_feed(self, **kwargs):
        posts = (
            request.env["tourism.post"]
            .sudo()
            .search([("is_published", "=", True)], order="create_date desc")
        )
        return request.render("tourism_provider_portal.tourism_feed", {"posts": posts})

    def _process_whatsapp_payload(self, payload):
        entries = payload.get("entry", [])
        partner_model = request.env["res.partner"].sudo()

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for message in messages:
                    wa_id = message.get("from")
                    if not wa_id:
                        continue

                    partner = partner_model.search([("whatsapp_number", "=", wa_id)], limit=1)
                    if not partner:
                        partner = partner_model.create(
                            {
                                "name": f"Usuario WhatsApp {wa_id}",
                                "whatsapp_number": wa_id,
                                "is_tourism_provider": True,
                                "chatbot_state": "start",
                                "tourism_approval_state": "draft",
                            }
                        )

                    approval_state = partner.tourism_approval_state
                    if approval_state == "approved":
                        partner._send_whatsapp_text_message(
                            "Ya fuiste aprobado. Revisa el enlace que te enviamos para acceder a tu perfil."
                        )
                        continue

                    if partner.chatbot_state == "start":
                        partner._send_whatsapp_text_message(
                            "¡Hola! Bienvenido al portal turístico. Para comenzar, envíame tu nombre completo."
                        )
                        partner.chatbot_state = "asking_name"
                        continue

                    if partner.chatbot_state == "asking_name":
                        text_body = ((message.get("text") or {}).get("body") or "").strip()
                        if text_body:
                            partner.write({"name": text_body, "chatbot_state": "asking_photo"})
                            partner._send_whatsapp_text_message(
                                "Gracias. Ahora envíame una foto de perfil."
                            )
                        else:
                            partner._send_whatsapp_text_message(
                                "Necesito tu nombre completo para continuar. Envíalo por texto, por favor."
                            )
                        continue

                    if partner.chatbot_state == "asking_photo":
                        image_data = message.get("image") or {}
                        media_id = image_data.get("id")
                        if not media_id:
                            partner._send_whatsapp_text_message(
                                "Necesito una foto para continuar. Envíame una imagen, por favor."
                            )
                            continue

                        try:
                            partner._download_and_store_whatsapp_image(media_id)
                            partner.write(
                                {
                                    "chatbot_state": "completed",
                                    "tourism_approval_state": "pending",
                                }
                            )
                            partner._send_whatsapp_text_message(
                                "Perfil completado. En revisión por el comité."
                            )
                        except Exception as exc:  # noqa: BLE001
                            _logger.exception("Error processing WhatsApp image: %s", exc)
                            partner._send_whatsapp_text_message(
                                "Hubo un error procesando tu imagen. Intenta enviarla nuevamente."
                            )
                        continue

                    if partner.chatbot_state == "completed":
                        partner._send_whatsapp_text_message(
                            "Tu perfil ya fue enviado a revisión. Te avisaremos por WhatsApp."
                        )

        _logger.debug("Processed WhatsApp payload: %s", json.dumps(payload))

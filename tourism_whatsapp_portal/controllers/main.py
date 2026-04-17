import base64
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class TourismWhatsAppController(http.Controller):
    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["GET"], csrf=False)
    def whatsapp_webhook_verify(self, **kwargs):
        mode = kwargs.get("hub.mode")
        token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")

        verify_token = request.env["res.partner"].sudo()._get_whatsapp_credentials()["verify_token"]
        if mode == "subscribe" and token and token == verify_token:
            return request.make_response(challenge or "", headers=[("Content-Type", "text/plain")])
        return request.make_response("Invalid verification token", status=403)

    @http.route("/whatsapp/webhook", type="http", auth="public", methods=["POST"], csrf=False)
    def whatsapp_webhook_receive(self):
        payload = request.httprequest.get_json(silent=True) or {}
        _logger.info("Webhook payload recibido: %s", json.dumps(payload))

        entries = payload.get("entry", [])
        partner_model = request.env["res.partner"].sudo()

        for entry in entries:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    from_number = message.get("from")
                    if not from_number:
                        continue

                    partner = partner_model.search([("whatsapp_number", "=", from_number)], limit=1)
                    if not partner:
                        partner = partner_model.create(
                            {
                                "name": from_number,
                                "is_tourism_provider": True,
                                "whatsapp_number": from_number,
                                "chatbot_state": "start",
                                "tourism_approval_state": "draft",
                            }
                        )

                    self._process_chatbot_state(partner, message)

        return request.make_json_response({"status": "ok"})

    def _process_chatbot_state(self, partner, message):
        message_type = message.get("type")
        text_body = (message.get("text") or {}).get("body")

        if partner.chatbot_state == "start":
            partner.write({"chatbot_state": "asking_name"})
            partner._send_whatsapp_message(partner.whatsapp_number, "¡Hola! Para iniciar, compárteme tu nombre.")
            return

        if partner.chatbot_state == "asking_name":
            if not text_body:
                partner._send_whatsapp_message(
                    partner.whatsapp_number,
                    "Necesito que me envíes tu nombre en texto.",
                )
                return
            partner.write({"name": text_body.strip(), "chatbot_state": "asking_photo"})
            partner._send_whatsapp_message(
                partner.whatsapp_number,
                "Gracias. Ahora envíame una foto de perfil.",
            )
            return

        if partner.chatbot_state == "asking_photo":
            if message_type != "image":
                partner._send_whatsapp_message(
                    partner.whatsapp_number,
                    "Para continuar, por favor envía una imagen.",
                )
                return

            media_id = (message.get("image") or {}).get("id")
            image_b64 = partner._download_whatsapp_media(media_id)
            if not image_b64:
                partner._send_whatsapp_message(
                    partner.whatsapp_number,
                    "No pude procesar la imagen. Intenta enviarla nuevamente.",
                )
                return

            partner.write(
                {
                    "image_1920": image_b64,
                    "chatbot_state": "completed",
                    "tourism_approval_state": "pending",
                }
            )
            partner._send_whatsapp_message(
                partner.whatsapp_number,
                "Perfil completado. En revisión por el comité.",
            )
            return

        partner._send_whatsapp_message(
            partner.whatsapp_number,
            "Tu perfil ya fue enviado al comité. Te avisaremos por este medio.",
        )


class TourismPortalController(http.Controller):
    @http.route("/my/tourism/profile", type="http", auth="user", website=True, methods=["GET", "POST"])
    def my_tourism_profile(self, **post):
        partner = request.env.user.partner_id.sudo()

        if request.httprequest.method == "POST":
            vals = {
                "name": post.get("name") or partner.name,
                "email": post.get("email") or partner.email,
                "phone": post.get("phone") or partner.phone,
            }
            cover_file = request.httprequest.files.get("cover_image")
            if cover_file:
                vals["cover_image"] = base64.b64encode(cover_file.read())
            partner.write(vals)
            return request.redirect("/my/tourism/profile")

        return request.render(
            "tourism_whatsapp_portal.portal_profile_template",
            {"partner": partner},
        )

    @http.route("/tourism/feed", type="http", auth="public", website=True)
    def tourism_feed(self, **kwargs):
        posts = request.env["tourism.post"].sudo().search([])
        return request.render(
            "tourism_whatsapp_portal.tourism_feed_template",
            {
                "posts": posts,
                "can_post": request.env.user._is_public() is False,
            },
        )

    @http.route("/tourism/post/create", type="http", auth="user", website=True, methods=["POST"])
    def create_tourism_post(self, **post):
        content = (post.get("content") or "").strip()
        if content:
            vals = {
                "content": content,
                "author_id": request.env.user.partner_id.id,
            }
            image_file = request.httprequest.files.get("image")
            if image_file:
                vals["image"] = base64.b64encode(image_file.read())
            request.env["tourism.post"].sudo().create(vals)
        return request.redirect("/tourism/feed")

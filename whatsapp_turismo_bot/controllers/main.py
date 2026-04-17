import logging

from odoo import http, _
from odoo.http import request, Response


_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):
    @http.route(
        "/whatsapp/webhook",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def whatsapp_webhook_verify(self, **kwargs):
        verify_token = kwargs.get("hub.verify_token")
        challenge = kwargs.get("hub.challenge")
        mode = kwargs.get("hub.mode")
        system_token = request.env["ir.config_parameter"].sudo().get_param(
            "whatsapp_turismo_bot.whatsapp_verify_token"
        )

        if mode == "subscribe" and verify_token and verify_token == system_token:
            return Response(challenge or "", status=200, content_type="text/plain")
        return Response("Forbidden", status=403)

    @http.route(
        "/whatsapp/webhook",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    def whatsapp_webhook_receive(self, **kwargs):
        try:
            payload = request.jsonrequest or {}
            self._process_payload(payload)
        except Exception:
            _logger.exception("Unexpected error while processing WhatsApp webhook")
        return {"status": "ok"}

    def _process_payload(self, payload):
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
                                "name": _("Usuario WhatsApp %s") % wa_id,
                                "whatsapp_number": wa_id,
                                "chatbot_state": "start",
                                "tourism_status": "draft",
                            }
                        )

                    self._advance_state(partner, message)

    def _advance_state(self, partner, message):
        state = partner.chatbot_state
        msg_type = message.get("type")
        text_body = (message.get("text") or {}).get("body", "").strip()

        if state == "start":
            partner.write({"chatbot_state": "asking_name"})
            partner._send_whatsapp_text_message(
                _(
                    "¡Hola! Bienvenido al portal de turismo. "
                    "Para registrarte, escribe tu nombre completo."
                )
            )
            return

        if state == "asking_name":
            if not text_body:
                partner._send_whatsapp_text_message(
                    _("Por favor, escribe tu nombre completo para continuar.")
                )
                return
            partner.write({"name": text_body, "chatbot_state": "asking_photo"})
            partner._send_whatsapp_text_message(
                _("¡Gracias! Ahora, por favor envíame una foto para tu perfil.")
            )
            return

        if state == "asking_photo":
            if msg_type != "image":
                partner._send_whatsapp_text_message(
                    _("Necesito una imagen para continuar. Por favor envía una foto.")
                )
                return
            media_id = (message.get("image") or {}).get("id")
            if not media_id:
                partner._send_whatsapp_text_message(
                    _("No encontré la imagen. Intenta enviarla de nuevo, por favor.")
                )
                return
            partner.action_process_whatsapp_photo(media_id)
            return

        if state == "in_review":
            partner._send_whatsapp_text_message(
                _("Tu perfil sigue en revisión. Te avisaremos cuando sea aprobado.")
            )
            return

        if state == "approved":
            partner._send_whatsapp_text_message(
                _("Tu perfil ya está aprobado. Gracias por comunicarte.")
            )

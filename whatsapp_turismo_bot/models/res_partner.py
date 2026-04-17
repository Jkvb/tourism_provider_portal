import base64
import logging

import requests

from odoo import _, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    whatsapp_number = fields.Char(string="WhatsApp Number", index=True)
    chatbot_state = fields.Selection(
        [
            ("start", "Start"),
            ("asking_name", "Asking Name"),
            ("asking_photo", "Asking Photo"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
        ],
        string="Chatbot State",
        default="start",
    )
    tourism_status = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
        ],
        string="Tourism Status",
        default="draft",
    )

    def _get_whatsapp_config(self):
        self.ensure_one()
        icp = self.env["ir.config_parameter"].sudo()
        return {
            "access_token": icp.get_param("whatsapp_turismo_bot.whatsapp_access_token"),
            "phone_number_id": icp.get_param("whatsapp_turismo_bot.whatsapp_phone_number_id"),
        }

    def _send_whatsapp_text_message(self, text):
        self.ensure_one()
        config = self._get_whatsapp_config()
        if not self.whatsapp_number or not config.get("access_token") or not config.get("phone_number_id"):
            return False

        endpoint = f"https://graph.facebook.com/v18.0/{config['phone_number_id']}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": self.whatsapp_number,
            "type": "text",
            "text": {"body": text},
        }
        headers = {
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            return True
        except requests.RequestException:
            _logger.exception("Error sending WhatsApp message to %s", self.whatsapp_number)
            return False

    def _download_and_store_whatsapp_image(self, media_id):
        self.ensure_one()
        config = self._get_whatsapp_config()
        access_token = config.get("access_token")
        if not access_token:
            return False

        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            metadata_url = f"https://graph.facebook.com/v18.0/{media_id}"
            metadata_response = requests.get(metadata_url, headers=headers, timeout=20)
            metadata_response.raise_for_status()
            media_url = metadata_response.json().get("url")
            if not media_url:
                return False

            media_response = requests.get(media_url, headers=headers, timeout=30)
            media_response.raise_for_status()
            encoded = base64.b64encode(media_response.content)
            self.write({"image_1920": encoded})
            return True
        except requests.RequestException:
            _logger.exception("Error downloading WhatsApp media %s", media_id)
            return False

    def action_process_whatsapp_photo(self, media_id):
        self.ensure_one()
        success = self._download_and_store_whatsapp_image(media_id)
        if not success:
            self._send_whatsapp_text_message(
                _("No pude procesar tu imagen. Intenta enviarla nuevamente, por favor.")
            )
            return False

        self.write({"chatbot_state": "in_review", "tourism_status": "pending"})
        self._send_whatsapp_text_message(
            _(
                "¡Excelente! Tu perfil ha sido completado y enviado al comité para su revisión."
            )
        )
        return True

    def action_approve_tourism(self):
        for partner in self:
            if partner.tourism_status != "pending":
                raise UserError(_("Solo puedes aprobar solicitudes en estado pendiente."))
            partner.write({"tourism_status": "approved", "chatbot_state": "approved"})
            partner._send_whatsapp_text_message(
                _("¡Felicidades! Tu perfil ha sido aprobado por el comité.")
            )
        return True

import base64
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_tourism_provider = fields.Boolean(string="Es prestador turístico", default=False)
    whatsapp_number = fields.Char(string="WhatsApp", index=True)
    chatbot_state = fields.Selection(
        [
            ("start", "Start"),
            ("asking_name", "Asking Name"),
            ("asking_photo", "Asking Photo"),
            ("completed", "Completed"),
        ],
        string="Estado del chatbot",
        default="start",
    )
    tourism_approval_state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending", "Pendiente"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
        ],
        string="Estado de aprobación",
        default="draft",
        tracking=True,
    )
    cover_image = fields.Image(string="Imagen de portada")

    _sql_constraints = [
        (
            "unique_whatsapp_number",
            "unique(whatsapp_number)",
            "El número de WhatsApp ya está registrado.",
        )
    ]

    def action_approve_provider(self):
        portal_group = self.env.ref("base.group_portal")

        for partner in self:
            if not partner.is_tourism_provider:
                raise UserError(_("El contacto no está marcado como prestador turístico."))
            if partner.tourism_approval_state != "pending":
                raise UserError(_("Solo se pueden aprobar prestadores en estado pendiente."))

            user = partner.user_ids[:1]
            if not user:
                login = partner.email or partner.whatsapp_number
                if not login:
                    raise UserError(
                        _("El prestador requiere email o número WhatsApp para generar usuario portal.")
                    )
                user = self.env["res.users"].sudo().create(
                    {
                        "name": partner.name or login,
                        "login": login,
                        "partner_id": partner.id,
                        "groups_id": [(6, 0, [portal_group.id])],
                    }
                )
            else:
                user.sudo().write({"groups_id": [(4, portal_group.id)]})

            partner.sudo().signup_prepare()
            signup_url = partner._get_signup_url_for_action()[partner.id]

            partner.write({"tourism_approval_state": "approved"})
            message = _(
                "¡Felicidades! Fuiste aprobado. Entra a este enlace para crear tu "
                "contraseña web y acceder a tu perfil: %s"
            ) % signup_url
            partner._send_whatsapp_message(partner.whatsapp_number, message)

        return True

    @api.model
    def _get_whatsapp_credentials(self):
        params = self.env["ir.config_parameter"].sudo()
        return {
            "verify_token": params.get_param("tourism_whatsapp_portal.verify_token"),
            "access_token": params.get_param("tourism_whatsapp_portal.access_token"),
            "phone_number_id": params.get_param("tourism_whatsapp_portal.phone_number_id"),
        }

    @api.model
    def _send_whatsapp_message(self, to_number, body):
        if not to_number:
            return False
        creds = self._get_whatsapp_credentials()
        if not creds["access_token"] or not creds["phone_number_id"]:
            _logger.warning("No hay credenciales de WhatsApp configuradas.")
            return False

        endpoint = f"https://graph.facebook.com/v18.0/{creds['phone_number_id']}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": body},
        }
        headers = {
            "Authorization": f"Bearer {creds['access_token']}",
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=20)
            response.raise_for_status()
            return True
        except requests.RequestException as exc:
            _logger.exception("Error enviando WhatsApp a %s: %s", to_number, exc)
            return False

    @api.model
    def _download_whatsapp_media(self, media_id):
        creds = self._get_whatsapp_credentials()
        if not creds["access_token"]:
            return False

        headers = {"Authorization": f"Bearer {creds['access_token']}"}
        media_endpoint = f"https://graph.facebook.com/v18.0/{media_id}"
        try:
            media_data = requests.get(media_endpoint, headers=headers, timeout=20).json()
            media_url = media_data.get("url")
            if not media_url:
                return False
            image_response = requests.get(media_url, headers=headers, timeout=20)
            image_response.raise_for_status()
            return base64.b64encode(image_response.content)
        except requests.RequestException:
            _logger.exception("No fue posible descargar el media_id %s", media_id)
            return False

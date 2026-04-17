import base64
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    is_tourism_provider = fields.Boolean(default=False)
    whatsapp_number = fields.Char(string="WhatsApp Number", index=True, copy=False)
    chatbot_state = fields.Selection(
        [
            ("start", "Start"),
            ("asking_name", "Asking Name"),
            ("asking_photo", "Asking Photo"),
            ("completed", "Completed"),
        ],
        default="start",
        string="Chatbot State",
    )
    tourism_approval_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
        string="Approval State",
    )
    cover_image = fields.Image(string="Cover Image")
    tourism_profile_description = fields.Text(string="Profile Description")

    _sql_constraints = [
        (
            "tourism_provider_whatsapp_number_uniq",
            "unique(whatsapp_number)",
            "WhatsApp Number must be unique.",
        ),
    ]

    def _get_whatsapp_config(self):
        config = self.env["ir.config_parameter"].sudo()
        return {
            "verify_token": config.get_param("tourism_provider_portal.verify_token"),
            "access_token": config.get_param("tourism_provider_portal.access_token"),
            "phone_number_id": config.get_param("tourism_provider_portal.phone_number_id"),
            "graph_api_version": config.get_param("tourism_provider_portal.graph_api_version") or "v18.0",
        }

    def _send_whatsapp_text_message(self, text):
        self.ensure_one()
        if not self.whatsapp_number:
            _logger.warning("Partner %s has no whatsapp_number", self.id)
            return False

        config = self._get_whatsapp_config()
        if not config.get("access_token") or not config.get("phone_number_id"):
            raise UserError(_("Missing Meta Cloud API configuration."))

        url = f"https://graph.facebook.com/{config['graph_api_version']}/{config['phone_number_id']}/messages"
        headers = {
            "Authorization": f"Bearer {config['access_token']}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": self.whatsapp_number,
            "type": "text",
            "text": {"body": text},
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code >= 300:
                _logger.error("Failed to send WhatsApp message: %s", response.text)
                return False
            return True
        except requests.RequestException as exc:
            _logger.exception("WhatsApp send failed: %s", exc)
            return False

    def _download_and_store_whatsapp_image(self, media_id):
        self.ensure_one()
        config = self._get_whatsapp_config()
        if not media_id:
            raise ValidationError(_("Media ID is required."))
        if not config.get("access_token"):
            raise UserError(_("Missing Meta Cloud API access token configuration."))

        headers = {"Authorization": f"Bearer {config['access_token']}"}
        api_version = config["graph_api_version"]
        media_meta_url = f"https://graph.facebook.com/{api_version}/{media_id}"

        try:
            meta_resp = requests.get(media_meta_url, headers=headers, timeout=30)
            meta_resp.raise_for_status()
            media_url = meta_resp.json().get("url")
            if not media_url:
                raise ValidationError(_("Unable to fetch media URL from Meta API."))

            image_resp = requests.get(media_url, headers=headers, timeout=30)
            image_resp.raise_for_status()

            self.image_1920 = base64.b64encode(image_resp.content)
            return True
        except requests.RequestException as exc:
            _logger.exception("Failed downloading WhatsApp image: %s", exc)
            raise UserError(_("Could not download the profile image from WhatsApp.")) from exc

    def action_approve_provider(self):
        portal_group = self.env.ref("base.group_portal")
        users_model = self.env["res.users"].sudo()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")

        for partner in self:
            if partner.tourism_approval_state != "pending":
                raise UserError(_("Provider must be in pending state to approve."))

            user = partner.user_ids[:1]
            if not user:
                login = partner.email or f"{partner.whatsapp_number or partner.id}@tourism-provider.local"
                values = {
                    "name": partner.name,
                    "partner_id": partner.id,
                    "login": login,
                    "email": partner.email or False,
                    "groups_id": [(6, 0, [portal_group.id])],
                }
                user = users_model.create(values)
            elif portal_group not in user.groups_id:
                user.write({"groups_id": [(4, portal_group.id)]})

            partner.sudo().signup_prepare()
            signup_map = partner.sudo()._get_signup_url_for_action()
            signup_url = signup_map.get(partner.id)
            if signup_url and signup_url.startswith("/") and base_url:
                signup_url = f"{base_url}{signup_url}"

            partner.write({"tourism_approval_state": "approved"})
            link_text = signup_url or _("Link unavailable. Contact support.")
            partner._send_whatsapp_text_message(
                _(
                    "¡Felicidades! Fuiste aprobado. Entra a este enlace para crear tu contraseña web y acceder a tu perfil: %s"
                )
                % link_text
            )
        return True

    def action_reject_provider(self):
        for partner in self:
            partner.write({"tourism_approval_state": "rejected"})
            partner._send_whatsapp_text_message(
                _(
                    "Tu solicitud fue rechazada por el comité. Puedes escribirnos por WhatsApp para más información."
                )
            )
        return True

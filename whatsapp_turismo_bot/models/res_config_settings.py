from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_verify_token = fields.Char(
        string="WhatsApp Verify Token",
        config_parameter="whatsapp_turismo_bot.whatsapp_verify_token",
    )
    whatsapp_access_token = fields.Char(
        string="WhatsApp Access Token",
        config_parameter="whatsapp_turismo_bot.whatsapp_access_token",
    )
    whatsapp_phone_number_id = fields.Char(
        string="WhatsApp Phone Number ID",
        config_parameter="whatsapp_turismo_bot.whatsapp_phone_number_id",
    )

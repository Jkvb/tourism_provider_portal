from odoo import fields, models


class TourismProviderImage(models.Model):
    _name = "tourism.provider.image"
    _description = "Galería de prestador turístico"
    _order = "sequence, id"

    provider_id = fields.Many2one("tourism.provider", required=True, ondelete="cascade", index=True)
    name = fields.Char(required=True)
    image_1920 = fields.Image(required=True)
    sequence = fields.Integer(default=10)

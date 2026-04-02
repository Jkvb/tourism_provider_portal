from odoo import fields, models


class TourismProviderCategory(models.Model):
    _name = "tourism.provider.category"
    _description = "Categoría de prestador turístico"
    _order = "sequence, name"

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    icon = fields.Char(help="Clase de ícono (por ejemplo: fa fa-hotel)")
    color = fields.Char(default="#2b6cb0", help="Color hexadecimal para la categoría")
    provider_count = fields.Integer(compute="_compute_provider_count")

    def _compute_provider_count(self):
        grouped = self.env["tourism.provider"]._read_group(
            [("category_id", "in", self.ids)], ["category_id"], ["__count"]
        )
        counts = {category.id: count for category, count in grouped}
        for category in self:
            category.provider_count = counts.get(category.id, 0)

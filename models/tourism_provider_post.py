from odoo import fields, models


class TourismProviderPost(models.Model):
    _name = "tourism.provider.post"
    _description = "Publicación de prestador turístico"
    _order = "create_date desc"

    provider_id = fields.Many2one("tourism.provider", required=True, ondelete="cascade", index=True)
    author_user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    body = fields.Text(required=True)
    image_1920 = fields.Image()
    is_published = fields.Boolean(default=True)
    create_date = fields.Datetime(readonly=True)

    def init(self):
        # Corrige instalaciones previas donde la columna se creó sin NOT NULL.
        self._cr.execute("UPDATE tourism_provider_post SET body = '' WHERE body IS NULL")
        self._cr.execute("ALTER TABLE tourism_provider_post ALTER COLUMN body SET NOT NULL")

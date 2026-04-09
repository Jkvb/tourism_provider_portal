from odoo import _, api, fields, models
from odoo.exceptions import AccessError


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

    @api.constrains("provider_id", "author_user_id")
    def _check_post_owner(self):
        for rec in self:
            if rec.author_user_id != rec.provider_id.portal_user_id and not self.env.user.has_group(
                "tourism_provider_portal.group_tourism_admin"
            ):
                raise AccessError(_("Solo el dueño del perfil puede crear publicaciones."))

    def init(self):
        self._cr.execute("UPDATE tourism_provider_post SET body = '' WHERE body IS NULL")
        self._cr.execute("ALTER TABLE tourism_provider_post ALTER COLUMN body SET NOT NULL")

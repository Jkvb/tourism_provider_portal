from odoo import _, api, fields, models
from odoo.exceptions import AccessError


class TourismPost(models.Model):
    _name = "tourism.post"
    _description = "Tourism Post"
    _order = "create_date desc"

    content = fields.Text(required=True)
    image = fields.Image()
    author_id = fields.Many2one("res.partner", required=True, ondelete="cascade")
    is_published = fields.Boolean(default=True)

    def _is_internal_admin(self):
        return self.env.user.has_group("base.group_system")

    @api.model_create_multi
    def create(self, vals_list):
        if not self._is_internal_admin():
            current_partner = self.env.user.partner_id
            for vals in vals_list:
                author_id = vals.get("author_id")
                if author_id and author_id != current_partner.id:
                    raise AccessError(_("You can only create posts for your own partner profile."))
                vals.setdefault("author_id", current_partner.id)
        return super().create(vals_list)

    def write(self, vals):
        if not self._is_internal_admin():
            current_partner = self.env.user.partner_id
            for post in self:
                if post.author_id != current_partner:
                    raise AccessError(_("You can only edit your own posts."))
                if vals.get("author_id") and vals["author_id"] != current_partner.id:
                    raise AccessError(_("You cannot reassign post ownership."))
        return super().write(vals)

    def unlink(self):
        if not self._is_internal_admin():
            current_partner = self.env.user.partner_id
            for post in self:
                if post.author_id != current_partner:
                    raise AccessError(_("You can only delete your own posts."))
        return super().unlink()

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import html_escape


class TourismProvider(models.Model):
    _name = "tourism.provider"
    _description = "Prestador turístico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, tracking=True)
    responsible_name = fields.Char(required=True)
    category_id = fields.Many2one("tourism.provider.category", required=True, index=True)
    description = fields.Html(sanitize=True)

    phone = fields.Char()
    whatsapp = fields.Char()
    email = fields.Char()
    street = fields.Char(string="Dirección")
    location_reference = fields.Char(string="Ubicación / referencia")
    city = fields.Char(string="Municipio")
    state_id = fields.Many2one("res.country.state", string="Estado")

    facebook_url = fields.Char()
    instagram_url = fields.Char()
    tiktok_url = fields.Char()
    website_url = fields.Char()

    schedule = fields.Text(string="Horarios")
    services_description = fields.Text(string="Servicios que ofrece")
    image_1920 = fields.Image(string="Imagen principal")
    profile_image_1920 = fields.Image(string="Foto de perfil")
    cover_image_1920 = fields.Image(string="Foto de portada")
    gallery_image_ids = fields.One2many("tourism.provider.image", "provider_id", string="Galería")
    post_ids = fields.One2many("tourism.provider.post", "provider_id", string="Publicaciones")

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("pending", "Pendiente de revisión"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
            ("published", "Publicado"),
            ("unpublished", "Despublicado"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )

    portal_user_id = fields.Many2one("res.users", string="Usuario portal", tracking=True)
    terms_accepted = fields.Boolean(string="Acepta términos", default=False)

    is_published = fields.Boolean(default=False, tracking=True)
    approval_user_id = fields.Many2one("res.users", string="Aprobado por")
    review_user_id = fields.Many2one("res.users", string="Revisado por")
    approval_date = fields.Datetime(string="Fecha de aprobación")
    review_date = fields.Datetime(string="Fecha de revisión")
    registration_date = fields.Datetime(string="Fecha de alta", default=fields.Datetime.now)
    rejection_reason = fields.Text(string="Motivo de rechazo")
    internal_notes = fields.Text(string="Observaciones internas")

    website_slug = fields.Char(compute="_compute_website_slug", store=True)

    _sql_constraints = [
        (
            "name_category_uniq",
            "unique(name, category_id)",
            "Ya existe un prestador con ese nombre en la categoría seleccionada.",
        )
    ]

    @api.depends("name")
    def _compute_website_slug(self):
        for record in self:
            safe_name = html_escape(record.name or "prestador")
            base = safe_name.lower().replace(" ", "-")
            slug = "".join(ch for ch in base if ch.isalnum() or ch == "-").strip("-")
            record.website_slug = slug or f"prestador-{record.id or 'nuevo'}"

    def _check_validator(self):
        if not self.user_has_groups(
            "tourism_provider_portal.group_tourism_admin,tourism_provider_portal.group_tourism_validator"
        ):
            raise AccessError(_("No tiene permisos para ejecutar esta acción."))

    def action_submit_for_review(self):
        for rec in self:
            if not rec.terms_accepted:
                raise UserError(_("Debe aceptar términos para enviar a revisión."))
            rec.write(
                {
                    "state": "pending",
                    "is_published": False,
                    "review_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                    "rejection_reason": False,
                }
            )
            rec.message_post(body=_("Solicitud enviada a revisión."))
        return True

    def action_submit_review(self):
        """Compatibilidad con vistas que usan el nombre corto del botón."""
        return self.action_submit_for_review()

    def action_approve(self):
        self._check_validator()
        for rec in self:
            rec.write(
                {
                    "state": "approved",
                    "approval_user_id": self.env.user.id,
                    "approval_date": fields.Datetime.now(),
                    "review_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                    "rejection_reason": False,
                }
            )
            rec.message_post(body=_("Prestador aprobado."))
        return True

    def action_reject(self):
        self._check_validator()
        for rec in self:
            if not rec.rejection_reason:
                raise UserError(_("Capture un motivo de rechazo antes de rechazar."))
            rec.write(
                {
                    "state": "rejected",
                    "is_published": False,
                    "review_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                }
            )
            rec.message_post(body=_("Prestador rechazado."))
        return True

    def action_publish(self):
        self._check_validator()
        for rec in self:
            if rec.state != "approved":
                raise UserError(_("Solo registros aprobados pueden publicarse."))
            rec.write({"state": "published", "is_published": True})
            rec.message_post(body=_("Prestador publicado en el portal."))
        return True

    def action_unpublish(self):
        self._check_validator()
        self.write({"state": "unpublished", "is_published": False})
        self.message_post(body=_("Prestador despublicado."))
        return True

    def action_back_to_draft(self):
        self.write({"state": "draft", "is_published": False, "rejection_reason": False})
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.message_post(body=_("Nuevo prestador registrado. Estado inicial: %s") % (rec.state,))
        return records

    def write(self, vals):
        tracked_fields = {
            "name",
            "responsible_name",
            "category_id",
            "description",
            "phone",
            "whatsapp",
            "email",
            "street",
            "location_reference",
            "city",
            "state_id",
            "facebook_url",
            "instagram_url",
            "tiktok_url",
            "website_url",
            "schedule",
            "services_description",
            "image_1920",
            "gallery_image_ids",
            "profile_image_1920",
            "cover_image_1920",
        }
        force_revalidation = bool(tracked_fields.intersection(vals.keys()))
        res = super().write(vals)
        for rec in self:
            if force_revalidation and rec.state in ("approved", "published"):
                rec.write({"state": "pending", "is_published": False})
                rec.message_post(
                    body=_(
                        "Se detectaron cambios posteriores a aprobación/publicación. "
                        "El registro volvió a pendiente de revisión."
                    )
                )
        return res

    def can_edit_from_portal(self):
        self.ensure_one()
        user = self.env.user
        return bool(user == self.portal_user_id or user.has_group("tourism_provider_portal.group_tourism_admin"))

    def portal_url(self):
        self.ensure_one()
        return f"/turismo/prestador/{self.website_slug}"

    def open_public_website(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "target": "new",
            "url": self.portal_url(),
        }

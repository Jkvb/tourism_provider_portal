import secrets

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request
from odoo.tools import html_escape


class TourismProvider(models.Model):
    _name = "tourism.provider"
    _description = "Prestador turístico"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(tracking=True)
    responsible_name = fields.Char()
    category_id = fields.Many2one("tourism.provider.category", index=True)
    description = fields.Html(sanitize=True)

    phone = fields.Char()
    email = fields.Char()
    signup_email = fields.Char(required=True, index=True, tracking=True)
    email_confirmed = fields.Boolean(default=False, tracking=True)
    confirmation_token = fields.Char(index=True, copy=False)
    confirmation_sent_date = fields.Datetime(copy=False)
    confirmation_date = fields.Datetime(readonly=True, copy=False)

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
            ("incomplete", "Perfil incompleto"),
            ("draft", "Borrador"),
            ("pending", "Pendiente de revisión"),
            ("approved", "Aprobado"),
            ("rejected", "Rechazado"),
            ("published", "Publicado"),
            ("unpublished", "Despublicado"),
        ],
        default="incomplete",
        tracking=True,
        index=True,
    )

    portal_user_id = fields.Many2one("res.users", string="Usuario portal", tracking=True, required=True)
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
    profile_completion = fields.Integer(compute="_compute_profile_completion")

    _sql_constraints = [
        ("tourism_provider_signup_email_uniq", "unique(signup_email)", "Este correo ya tiene un perfil registrado."),
    ]

    @api.depends("name")
    def _compute_website_slug(self):
        for record in self:
            safe_name = html_escape(record.name or record.signup_email or "prestador")
            base = safe_name.lower().replace(" ", "-")
            slug = "".join(ch for ch in base if ch.isalnum() or ch == "-").strip("-")
            record.website_slug = slug or f"prestador-{record.id or 'nuevo'}"

    @api.depends(
        "name",
        "responsible_name",
        "phone",
        "description",
        "category_id",
        "street",
        "schedule",
        "services_description",
        "profile_image_1920",
        "cover_image_1920",
    )
    def _compute_profile_completion(self):
        fields_to_check = [
            "name",
            "responsible_name",
            "phone",
            "description",
            "category_id",
            "street",
            "schedule",
            "services_description",
            "profile_image_1920",
            "cover_image_1920",
        ]
        for rec in self:
            filled = sum(1 for field_name in fields_to_check if rec[field_name])
            rec.profile_completion = int((filled / len(fields_to_check)) * 100)

    def _check_validator(self):
        if not self.user_has_groups(
            "tourism_provider_portal.group_tourism_admin,tourism_provider_portal.group_tourism_validator"
        ):
            raise AccessError(_("No tiene permisos para ejecutar esta acción."))

    def _is_profile_complete(self):
        self.ensure_one()
        required_fields = [
            self.name,
            self.responsible_name,
            self.phone,
            self.description,
            self.category_id,
            self.street,
            self.schedule,
            self.services_description,
            self.profile_image_1920,
            self.cover_image_1920,
        ]
        return all(required_fields)

    def action_submit_for_review(self):
        for rec in self:
            if not rec.email_confirmed:
                raise UserError(_("Debes confirmar tu correo antes de enviar tu perfil a revisión."))
            if not rec._is_profile_complete():
                raise UserError(_("Completa tu perfil antes de enviarlo a revisión."))
            rec.write(
                {
                    "state": "pending",
                    "is_published": False,
                    "review_user_id": self.env.user.id,
                    "review_date": fields.Datetime.now(),
                    "rejection_reason": False,
                    "terms_accepted": True,
                }
            )
            rec.message_post(body=_("Solicitud enviada a revisión."))
        return True

    def action_submit_review(self):
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
        self.write({"state": "incomplete", "is_published": False, "rejection_reason": False})
        return True

    def regenerate_confirmation_token(self):
        for rec in self:
            rec.write(
                {
                    "confirmation_token": secrets.token_urlsafe(32),
                    "confirmation_sent_date": fields.Datetime.now(),
                }
            )

    def get_confirmation_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return f"{base_url}/turismo/confirmar/{self.confirmation_token}"

    def action_send_confirmation_email(self):
        template = self.env.ref("tourism_provider_portal.mail_template_tourism_provider_confirmation", raise_if_not_found=False)
        for rec in self:
            if not rec.confirmation_token:
                rec.regenerate_confirmation_token()
            if template:
                template.sudo().send_mail(rec.id, force_send=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec.message_post(body=_("Nuevo prestador registrado. Estado inicial: %s") % (rec.state,))
        return records

    @api.constrains("signup_email")
    def _check_signup_email(self):
        for rec in self:
            if not rec.signup_email:
                continue
            login_exists = self.env["res.users"].sudo().search_count([("login", "=", rec.signup_email), ("id", "!=", rec.portal_user_id.id)])
            if login_exists:
                raise ValidationError(_("Este correo ya está vinculado a otra cuenta."))

    def write(self, vals):
        tracked_fields = {
            "name",
            "responsible_name",
            "category_id",
            "description",
            "phone",
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
                super(TourismProvider, rec).write({"state": "pending", "is_published": False})
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

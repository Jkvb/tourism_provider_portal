from odoo import fields, models


class TourismPost(models.Model):
    _name = "tourism.post"
    _description = "Publicación turística"
    _order = "create_date desc"

    content = fields.Text(string="Contenido", required=True)
    image = fields.Image(string="Imagen")
    author_id = fields.Many2one("res.partner", string="Autor", required=True, ondelete="cascade")

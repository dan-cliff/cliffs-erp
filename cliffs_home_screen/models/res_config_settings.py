from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cliffs_home_background_color = fields.Char(
        related='company_id.cliffs_home_background_color', readonly=False)
    cliffs_home_background_image = fields.Binary(
        related='company_id.cliffs_home_background_image', readonly=False)
    cliffs_home_background_opacity = fields.Integer(
        related='company_id.cliffs_home_background_opacity', readonly=False)

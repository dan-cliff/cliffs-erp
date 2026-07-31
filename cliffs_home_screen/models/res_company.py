from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    cliffs_home_background_color = fields.Char(string='Home Screen Background Color')
    cliffs_home_background_image = fields.Binary(
        string='Home Screen Background Image', attachment=True)
    cliffs_home_background_opacity = fields.Integer(
        string='Home Screen Background Image Opacity',
        default=100,
        help='How visible the background image is over the background color (0-100).',
    )

from odoo import fields, models


class SeeanceWorkLocation(models.Model):
    _name = 'seeance.work_location'
    _description = 'Seeance Work Location'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

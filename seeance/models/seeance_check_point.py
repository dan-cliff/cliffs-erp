from odoo import fields, models


class SeeanceCheckPoint(models.Model):
    _name = 'seeance.check_point'
    _description = 'Seeance Check Point'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    work_location_id = fields.Many2one(
        'hr.work.location', string='Work Location', required=True,
        domain="[('company_id', '=', company_id)]",
        help='The work location workers sign in to at this Check Point.')

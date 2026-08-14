from odoo import fields, models


class SeeanceCheckPoint(models.Model):
    _inherit = 'seeance.check_point'

    allow_visitor_registration = fields.Boolean(
        string='Allow Visitor Registration',
        help='Allow visitors (non-employees) to register themselves in at this Check Point.')
    visitor_question_ids = fields.One2many(
        'seeance.visitor.question', 'check_point_id', string='Visitor Questions')

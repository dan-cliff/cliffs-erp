from odoo import fields, models


class SeeanceVisitorQuestion(models.Model):
    _name = 'seeance.visitor.question'
    _description = 'Seeance Visitor Registration Question'
    _order = 'sequence, id'

    check_point_id = fields.Many2one(
        'seeance.check_point', string='Check Point', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Question', required=True)
    is_required = fields.Boolean(string='Required', default=True)

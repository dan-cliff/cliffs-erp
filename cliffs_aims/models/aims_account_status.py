from odoo import fields, models


class AimsAccountStatus(models.Model):
    _name = 'aims.account.status'
    _description = 'AIMS Account Status'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

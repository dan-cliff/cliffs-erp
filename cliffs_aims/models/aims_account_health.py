from odoo import fields, models


class AimsAccountHealth(models.Model):
    _name = 'aims.account.health'
    _description = 'AIMS Account Health'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

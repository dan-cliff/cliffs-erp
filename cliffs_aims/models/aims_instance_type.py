from odoo import fields, models


class AimsInstanceType(models.Model):
    _name = 'aims.instance.type'
    _description = 'AIMS Instance Type'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

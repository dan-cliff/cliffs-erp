from odoo import fields, models


class AimsAccountPackage(models.Model):
    _name = 'aims.account.package'
    _description = 'AIMS Account Package'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

from odoo import fields, models


class AimsCloudProvider(models.Model):
    _name = 'aims.cloud.provider'
    _description = 'AIMS Cloud Provider'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

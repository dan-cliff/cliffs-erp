from odoo import fields, models


class AimsServer(models.Model):
    _name = 'aims.server'
    _description = 'AIMS Server'
    _order = 'name'

    name = fields.Char(required=True)
    cloud_provider_id = fields.Many2one(
        'aims.cloud.provider', string='Cloud Provider', required=True)
    active = fields.Boolean(default=True)

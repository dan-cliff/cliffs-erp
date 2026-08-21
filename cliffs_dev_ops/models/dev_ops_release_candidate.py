from odoo import fields, models


class DevOpsReleaseCandidate(models.Model):
    _name = 'dev.ops.release.candidate'
    _description = 'Release Candidate'
    _order = 'sequence, name'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A release candidate with this name already exists.'),
    ]

from odoo import api, fields, models


class CliffsLoginNonce(models.Model):
    _name = 'cliffs.login.nonce'
    _description = 'Consumed Cliffs System Manager login tokens (replay protection)'

    nonce = fields.Char(required=True, index=True)

    @api.autovacuum
    def _gc_expired(self):
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        self.search([('create_date', '<', cutoff)]).unlink()

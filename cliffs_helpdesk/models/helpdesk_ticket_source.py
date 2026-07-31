from odoo import fields, models


class HelpdeskTicketSource(models.Model):
    _name = 'helpdesk.ticket.source'
    _description = 'Helpdesk Ticket Source'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

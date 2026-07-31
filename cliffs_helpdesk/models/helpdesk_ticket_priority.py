from odoo import fields, models


class HelpdeskTicketPriority(models.Model):
    _name = 'helpdesk.ticket.priority'
    _description = 'Helpdesk Ticket Priority'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(
        default=10, help='Higher values are treated as more urgent.')
    color = fields.Integer(string='Color')
    active = fields.Boolean(default=True)

from odoo import fields, models


class HelpdeskTicketStage(models.Model):
    _name = 'helpdesk.ticket.stage'
    _description = 'Helpdesk Ticket Stage'
    _order = 'sequence, id'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(
        string='Folded in Kanban',
        help='This stage is folded in the kanban view when it has no tickets to display.')
    is_closed = fields.Boolean(
        string='Closing Stage',
        help='Tickets reaching this stage are considered closed/resolved.')
    description = fields.Text(translate=True)
    active = fields.Boolean(default=True)

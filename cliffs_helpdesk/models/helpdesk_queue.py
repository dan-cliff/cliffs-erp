import ast

from odoo import api, fields, models


class HelpdeskQueue(models.Model):
    _name = 'helpdesk.queue'
    _inherit = ['mail.alias.mixin', 'mail.thread']
    _description = 'Helpdesk Queue'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    description = fields.Text()
    color = fields.Integer(string='Color')

    manager_id = fields.Many2one(
        'res.users', string='Team Leader', tracking=True,
        domain=[('share', '=', False)])
    agent_ids = fields.Many2many(
        'res.users', 'helpdesk_queue_agent_rel', 'queue_id', 'user_id',
        string='Agents', domain=[('share', '=', False)],
        help='Users allocated to this queue. Agents only see tickets in '
             'queues they belong to; Helpdesk Managers see every queue.')

    ticket_ids = fields.One2many('helpdesk.ticket', 'queue_id', string='Tickets')
    ticket_count = fields.Integer(compute='_compute_ticket_count')

    alias_id = fields.Many2one(
        help='Emails sent to this alias automatically create a new ticket '
             'in this queue.')

    @api.depends('ticket_ids')
    def _compute_ticket_count(self):
        for queue in self:
            queue.ticket_count = len(queue.ticket_ids)

    def _alias_get_creation_values(self):
        values = super()._alias_get_creation_values()
        values['alias_model_id'] = self.env['ir.model']._get_id('helpdesk.ticket')
        if self.id:
            existing_defaults = values.get('alias_defaults') or '{}'
            defaults = existing_defaults if isinstance(existing_defaults, dict) \
                else ast.literal_eval(existing_defaults)
            defaults['queue_id'] = self.id
            values['alias_defaults'] = defaults
        return values

    def action_view_tickets(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('cliffs_helpdesk.helpdesk_ticket_action')
        action['domain'] = [('queue_id', '=', self.id)]
        action['context'] = {'default_queue_id': self.id}
        return action

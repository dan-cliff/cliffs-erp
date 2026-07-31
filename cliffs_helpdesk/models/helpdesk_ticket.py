from odoo import api, fields, models, _


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority_sequence desc, id desc'
    _rec_name = 'name'

    name = fields.Char(string='Subject', required=True, tracking=True)
    ticket_ref = fields.Char(string='Reference', copy=False, readonly=True, default=lambda self: _('New'))
    description = fields.Html()
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)

    queue_id = fields.Many2one(
        'helpdesk.queue', string='Queue', required=True, tracking=True, index=True)
    stage_id = fields.Many2one(
        'helpdesk.ticket.stage', string='Stage', tracking=True, index=True, copy=False,
        group_expand='_read_group_stage_ids',
        default=lambda self: self.env['helpdesk.ticket.stage'].search([], order='sequence, id', limit=1))
    priority_id = fields.Many2one(
        'helpdesk.ticket.priority', string='Priority', tracking=True,
        default=lambda self: self.env['helpdesk.ticket.priority'].search([], order='sequence, id', limit=1))
    priority_sequence = fields.Integer(
        related='priority_id.sequence', store=True, string='Priority Sequence')
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string='Type', tracking=True)
    source_id = fields.Many2one('helpdesk.ticket.source', string='Source', tracking=True)
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags')

    partner_id = fields.Many2one('res.partner', string='Contact', tracking=True)
    partner_company_id = fields.Many2one(
        'res.partner', string='Company', tracking=True,
        compute='_compute_partner_company_id', store=True, readonly=False,
        domain=[('is_company', '=', True)])
    partner_email = fields.Char(string='Email')
    partner_phone = fields.Char(string='Phone')

    user_id = fields.Many2one('res.users', string='Assigned Agent', tracking=True, index=True)
    is_closed = fields.Boolean(related='stage_id.is_closed', string='Closed', store=True)
    date_closed = fields.Datetime(string='Closed On', readonly=True, copy=False)
    date_deadline = fields.Datetime(string='Deadline', tracking=True)

    @api.depends('partner_id')
    def _compute_partner_company_id(self):
        for ticket in self:
            commercial_partner = ticket.partner_id.commercial_partner_id
            if commercial_partner.is_company:
                ticket.partner_company_id = commercial_partner
            elif not ticket.partner_company_id:
                ticket.partner_company_id = False

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_email = self.partner_id.email
            self.partner_phone = self.partner_id.phone

    @api.model
    def _read_group_stage_ids(self, stages, domain, order=None):
        return stages.search([], order='sequence, id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('ticket_ref', _('New')) == _('New'):
                vals['ticket_ref'] = self.env['ir.sequence'].next_by_code('helpdesk.ticket') or _('New')
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('stage_id'):
            stage = self.env['helpdesk.ticket.stage'].browse(vals['stage_id'])
            vals.setdefault('date_closed', fields.Datetime.now() if stage.is_closed else False)
        return super().write(vals)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = dict(custom_values or {})
        values.setdefault('name', msg_dict.get('subject') or _('New Ticket'))
        values.setdefault('description', msg_dict.get('body'))
        values.setdefault('partner_email', msg_dict.get('email_from'))
        if msg_dict.get('author_id'):
            values.setdefault('partner_id', msg_dict['author_id'])
        if not values.get('source_id'):
            source = self.env.ref('cliffs_helpdesk.helpdesk_ticket_source_email', raise_if_not_found=False)
            if source:
                values['source_id'] = source.id
        return super().message_new(msg_dict, custom_values=values)

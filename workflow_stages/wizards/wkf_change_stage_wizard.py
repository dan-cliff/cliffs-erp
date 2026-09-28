# Part of Cliffs. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class WkfChangeStageWizard(models.TransientModel):
    """"Change Stage" dialog — shows every transition currently available from
    the target record's stage, each labelled with a direction arrow, and
    applies the one the user picks.
    """

    _name = 'wkf.change.stage.wizard'
    _description = 'Change Workflow Stage'

    res_model = fields.Char(string='Related Model', required=True)
    res_id = fields.Integer(string='Related Record', required=True)

    record_display_name = fields.Char(compute='_compute_record_info', readonly=True)
    current_stage_id = fields.Many2one('wkf.stage', compute='_compute_record_info', readonly=True)

    transition_ids = fields.Many2many(
        'wkf.transition',
        compute='_compute_transition_ids',
        string='Available Transitions',
    )
    selected_transition_id = fields.Many2one(
        'wkf.transition',
        string='New Stage',
        domain="[('id', 'in', transition_ids)]",
    )
    note = fields.Text(string='Note', help='Optional note logged on the record alongside the stage change.')

    def _get_target_record(self):
        self.ensure_one()
        if not self.res_model or self.res_model not in self.env:
            return None
        return self.env[self.res_model].browse(self.res_id)

    @api.depends('res_model', 'res_id')
    def _compute_record_info(self):
        for wizard in self:
            record = wizard._get_target_record()
            if record is not None and record.exists():
                wizard.record_display_name = record.display_name
                wizard.current_stage_id = record.wkf_stage_id
            else:
                wizard.record_display_name = False
                wizard.current_stage_id = False

    @api.depends('res_model', 'res_id')
    def _compute_transition_ids(self):
        for wizard in self:
            record = wizard._get_target_record()
            if (
                record is not None
                and record.exists()
                and hasattr(record, '_wkf_get_available_transitions')
            ):
                wizard.transition_ids = record._wkf_get_available_transitions(manual=True)
            else:
                wizard.transition_ids = False

    def action_confirm(self):
        self.ensure_one()
        if not self.selected_transition_id:
            raise UserError(_('Please select a stage to move this record to.'))
        record = self._get_target_record()
        if record is None or not record.exists():
            raise UserError(_('The related record could not be found.'))
        record.action_wkf_apply_transition(self.selected_transition_id.id, manual=True)
        if self.note and hasattr(record, 'message_post'):
            record.message_post(body=self.note)
        return {'type': 'ir.actions.act_window_close'}

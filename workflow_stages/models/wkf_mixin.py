# Part of Cliffs. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class WkfStageMixin(models.AbstractModel):
    """Inherit this on any model to plug it into the Workflow Stages engine.

    Adds a `wkf_stage_id` field (the record's current stage) plus the
    methods needed to discover and apply transitions, either manually
    (through the "Change Stage" wizard) or programmatically (from a server
    action, automation rule, or any other calling code).

    A consuming module is expected to add its own button to call
    `action_wkf_open_change_stage_wizard()`, e.g.::

        <button name="action_wkf_open_change_stage_wizard"
                type="object" string="Change Stage"/>
    """

    _name = 'wkf.stage.mixin'
    _description = 'Workflow Stage Mixin'

    wkf_workflow_id = fields.Many2one(
        'wkf.workflow',
        string='Workflow',
        compute='_compute_wkf_workflow_id',
        store=True,
        index=True,
    )
    wkf_stage_id = fields.Many2one(
        'wkf.stage',
        string='Workflow Stage',
        tracking=True,
        copy=False,
        index=True,
        domain="[('workflow_id', '=', wkf_workflow_id)]",
    )

    @api.depends()
    def _compute_wkf_workflow_id(self):
        workflow = self.env['wkf.workflow'].sudo().search(
            [('model_name', '=', self._name), ('active', '=', True)], limit=1,
        )
        for record in self:
            record.wkf_workflow_id = workflow.id if workflow else False

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if not record.wkf_stage_id and record.wkf_workflow_id:
                initial_stage = record.wkf_workflow_id.stage_ids.filtered('is_initial')[:1]
                if initial_stage:
                    record.with_context(wkf_bypass_check=True).write({
                        'wkf_stage_id': initial_stage.id,
                    })
        return records

    def write(self, vals):
        if 'wkf_stage_id' in vals and not self.env.context.get('wkf_bypass_check'):
            new_stage = (
                self.env['wkf.stage'].browse(vals['wkf_stage_id'])
                if vals['wkf_stage_id'] else self.env['wkf.stage']
            )
            for record in self:
                old_stage = record.wkf_stage_id
                if not (new_stage and old_stage and old_stage != new_stage):
                    continue
                if not old_stage.workflow_id.transition_ids:
                    # No transitions modelled yet for this workflow — allow
                    # free-form stage assignment.
                    continue
                valid = old_stage.workflow_id.transition_ids.filtered(
                    lambda t: t.from_stage_id == old_stage and t.to_stage_id == new_stage
                )
                if not valid:
                    raise ValidationError(_(
                        'No workflow transition connects stage "%(from)s" to "%(to)s".'
                    ) % {'from': old_stage.name, 'to': new_stage.name})
        return super().write(vals)

    def _wkf_get_available_transitions(self, manual=True):
        """Return the transitions that may currently be applied from this record's stage."""
        self.ensure_one()
        if not self.wkf_stage_id:
            return self.env['wkf.transition']
        user = self.env.user if manual else None
        transitions = self.wkf_stage_id.out_transition_ids.sorted('sequence')
        return transitions.filtered(lambda t: t.is_available(record=self, user=user, manual=manual))

    def action_wkf_open_change_stage_wizard(self):
        """Open the "Change Stage" wizard for this record."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Change Workflow Stage'),
            'res_model': 'wkf.change.stage.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }

    def action_wkf_apply_transition(self, transition_id, manual=True):
        """Apply `transition_id` to this record.

        Called by the "Change Stage" wizard (manual=True) or by any other
        code — a server action, an automation rule, a cron — wanting to
        move the record forward programmatically (manual=False).
        """
        self.ensure_one()
        transition = self.env['wkf.transition'].browse(transition_id)
        if not transition.exists():
            raise UserError(_('The selected transition no longer exists.'))
        if transition.from_stage_id != self.wkf_stage_id:
            raise UserError(_(
                'The "%s" transition no longer applies — this record is no '
                'longer in its origin stage.'
            ) % transition.name)

        user = self.env.user if manual else None
        if not transition.is_available(record=self, user=user, manual=manual):
            raise UserError(_(
                'The "%s" transition is not currently available for this record.'
            ) % transition.name)

        self.with_context(wkf_bypass_check=True).write({
            'wkf_stage_id': transition.to_stage_id.id,
        })

        if hasattr(self, 'message_post'):
            try:
                self.message_post(body=_(
                    'Workflow stage changed: %(from)s → %(to)s (%(transition)s)'
                ) % {
                    'from': transition.from_stage_id.name,
                    'to': transition.to_stage_id.name,
                    'transition': transition.name,
                })
            except Exception:
                pass
        return True

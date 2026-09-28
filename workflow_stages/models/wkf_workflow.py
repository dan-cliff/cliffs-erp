# Part of Cliffs. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class WkfWorkflow(models.Model):
    """A workflow definition: a graph of Stages connected by Transitions.

    Exactly one active workflow is supported per target model — the
    `wkf.stage.mixin` looks it up by `model_name` to decide which workflow
    (if any) governs a given business model.
    """

    _name = 'wkf.workflow'
    _description = 'Workflow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    description = fields.Html(string='Description')

    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        ondelete='cascade',
        domain=[('transient', '=', False)],
        tracking=True,
        help='The model this workflow governs. Records of this model must '
             'inherit "wkf.stage.mixin" to use it.',
    )
    model_name = fields.Char(
        related='model_id.model',
        string='Model Name',
        store=True,
        readonly=True,
    )

    stage_ids = fields.One2many(
        'wkf.stage',
        'workflow_id',
        string='Stages',
        copy=True,
    )
    transition_ids = fields.One2many(
        'wkf.transition',
        'workflow_id',
        string='Transitions',
        copy=True,
    )

    stage_count = fields.Integer(string='Stages', compute='_compute_counts')
    transition_count = fields.Integer(string='Transitions', compute='_compute_counts')

    # Canvas viewport state (remembered per workflow)
    canvas_zoom = fields.Float(string='Canvas Zoom', default=1.0)
    canvas_pan_x = fields.Float(string='Canvas Pan X', default=60.0)
    canvas_pan_y = fields.Float(string='Canvas Pan Y', default=60.0)

    @api.depends('stage_ids', 'transition_ids')
    def _compute_counts(self):
        for workflow in self:
            workflow.stage_count = len(workflow.stage_ids)
            workflow.transition_count = len(workflow.transition_ids)

    @api.constrains('model_id', 'active')
    def _check_unique_active_workflow_per_model(self):
        for workflow in self:
            if not workflow.active or not workflow.model_id:
                continue
            other = self.search([
                ('id', '!=', workflow.id),
                ('model_id', '=', workflow.model_id.id),
                ('active', '=', True),
            ], limit=1)
            if other:
                raise ValidationError(_(
                    'Another active workflow ("%s") already governs the model "%s". '
                    'Archive it first, or choose a different model.'
                ) % (other.name, workflow.model_id.display_name))

    def action_open_canvas(self):
        """Open the visual canvas editor for this workflow."""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'workflow_stages.canvas',
            'name': _('Canvas — %s') % self.name,
            'params': {'workflow_id': self.id},
            'context': {'workflow_id': self.id},
        }

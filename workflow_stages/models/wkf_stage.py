# Part of Cliffs. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class WkfStage(models.Model):
    """A single stage within a workflow.

    Stages are positioned on the visual canvas (`canvas_x` / `canvas_y`) and
    connected to one another by `wkf.transition` records.
    """

    _name = 'wkf.stage'
    _description = 'Workflow Stage'
    _order = 'sequence, id'

    workflow_id = fields.Many2one(
        'wkf.workflow',
        string='Workflow',
        required=True,
        ondelete='cascade',
        index=True,
    )
    name = fields.Char(string='Stage Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)

    is_initial = fields.Boolean(
        string='Initial Stage',
        help='New records are placed in this stage automatically. '
             'Only one stage per workflow may be marked as initial.',
    )
    is_final = fields.Boolean(
        string='Final Stage',
        help='Marks this stage as an end-point of the workflow (for display purposes only).',
    )

    # ------------------------------------------------------------------ #
    # Canvas layout                                                        #
    # ------------------------------------------------------------------ #

    canvas_x = fields.Float(string='Canvas X', default=100.0)
    canvas_y = fields.Float(string='Canvas Y', default=100.0)

    out_transition_ids = fields.One2many(
        'wkf.transition', 'from_stage_id', string='Outgoing Transitions',
        copy=False,
    )
    in_transition_ids = fields.One2many(
        'wkf.transition', 'to_stage_id', string='Incoming Transitions',
        copy=False,
    )

    # ------------------------------------------------------------------ #
    # Allowed users — filtered against res.users with the standard        #
    # Odoo filter-builder widget.                                         #
    # ------------------------------------------------------------------ #

    user_domain = fields.Char(
        string='Allowed Users Filter',
        default='[]',
        help='Restricts which users are considered "allowed" for this stage '
             '(e.g. eligible to be responsible for a record while it sits '
             'here, or to manually trigger a transition that restricts '
             'itself to "Origin Stage Allowed Users"). Leave empty to allow '
             'any user.',
    )
    # Constant helper so the domain widget knows which model to build its
    # graphical filter against (the widget reads this field's stored value).
    res_users_model = fields.Char(default='res.users')

    allowed_user_count = fields.Integer(
        string='Allowed Users',
        compute='_compute_allowed_user_count',
        help='Number of users currently matching the Allowed Users Filter.',
    )

    @api.depends('user_domain')
    def _compute_allowed_user_count(self):
        Users = self.env['res.users']
        for stage in self:
            try:
                domain = safe_eval.safe_eval(stage.user_domain or '[]')
            except Exception:
                _logger.exception(
                    "wkf.stage '%s' — error evaluating user_domain", stage.name,
                )
                domain = []
            stage.allowed_user_count = Users.search_count(domain)

    @api.constrains('workflow_id', 'is_initial')
    def _check_single_initial_stage(self):
        for stage in self:
            if not stage.is_initial:
                continue
            other = self.search([
                ('id', '!=', stage.id),
                ('workflow_id', '=', stage.workflow_id.id),
                ('is_initial', '=', True),
            ], limit=1)
            if other:
                raise ValidationError(_(
                    'Workflow "%s" already has an initial stage ("%s"). '
                    'Only one stage may be marked as initial.'
                ) % (stage.workflow_id.name, other.name))

    def action_duplicate(self, offset_x=30, offset_y=30):
        """Create a copy of this stage without any transitions and return its ID."""
        self.ensure_one()
        new_stage = self.copy(default={
            'canvas_x': self.canvas_x + offset_x,
            'canvas_y': self.canvas_y + offset_y,
            'name': _('%s (copy)') % self.name,
            'is_initial': False,
        })
        return new_stage.id

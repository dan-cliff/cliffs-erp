# Part of Cliffs. See LICENSE file for full copyright and licensing details.

import logging

from odoo import _, api, fields, models
from odoo.tools import safe_eval

_logger = logging.getLogger(__name__)


class WkfTransition(models.Model):
    """A directed, conditional connection between two workflow stages.

    A transition may be followed manually (offered to a user through the
    "Change Stage" wizard) and/or automatically (applied from a server
    action, automation rule, or any other code calling
    ``record.action_wkf_apply_transition(transition.id, manual=False)``).
    """

    _name = 'wkf.transition'
    _description = 'Workflow Transition'
    _order = 'sequence, id'

    workflow_id = fields.Many2one(
        'wkf.workflow',
        string='Workflow',
        related='from_stage_id.workflow_id',
        store=True,
        index=True,
        readonly=True,
    )
    from_stage_id = fields.Many2one(
        'wkf.stage',
        string='From Stage',
        required=True,
        ondelete='cascade',
        index=True,
    )
    to_stage_id = fields.Many2one(
        'wkf.stage',
        string='To Stage',
        required=True,
        ondelete='cascade',
        index=True,
        domain="[('workflow_id', '=', workflow_id)]",
    )
    name = fields.Char(string='Label', required=True, default=lambda self: _('Transition'))
    sequence = fields.Integer(
        string='Sequence', default=10,
        help='When several transitions leave the same stage, this controls '
             'the order they are offered in.',
    )

    direction = fields.Selection(
        selection=[
            ('forward', 'Forward'),
            ('backward', 'Backward'),
        ],
        string='Direction',
        required=True,
        default='forward',
        help='Purely descriptive: drives the arrow shown to the user when '
             'this transition is offered (e.g. a "Forward" approval vs. a '
             '"Backward" rejection/rework step).',
    )

    # ------------------------------------------------------------------ #
    # Manual vs. automatic availability                                    #
    # ------------------------------------------------------------------ #

    allow_manual = fields.Boolean(
        string='Allow Manual Trigger',
        default=True,
        help='Users may apply this transition themselves via the "Change Stage" action.',
    )
    allow_automatic = fields.Boolean(
        string='Allow Automatic Trigger',
        default=True,
        help='This transition may be applied programmatically — from a server '
             'action, automation rule, or scheduled action — without a user '
             'in the loop.',
    )

    # ------------------------------------------------------------------ #
    # Record condition                                                     #
    # ------------------------------------------------------------------ #

    record_condition_type = fields.Selection(
        selection=[
            ('none', 'No Condition'),
            ('domain', 'Domain Filter'),
            ('python', 'Python Expression'),
        ],
        string='Record Condition',
        default='none',
        required=True,
    )
    record_condition_domain = fields.Char(
        string='Condition Domain',
        default='[]',
        help='Odoo domain evaluated against the record being transitioned.',
    )
    record_condition_python = fields.Text(
        string='Condition Python',
        help='Python expression returning True/False. '
             'Available: record, env, user.',
    )
    # Exposes the workflow's target model name so the domain widget can
    # present the graphical filter builder for the record condition.
    workflow_model_name = fields.Char(
        related='workflow_id.model_name',
        readonly=True,
        store=False,
    )

    # ------------------------------------------------------------------ #
    # Manual-trigger user restriction                                      #
    # ------------------------------------------------------------------ #

    user_restriction_type = fields.Selection(
        selection=[
            ('any', 'Any User'),
            ('stage_users', "Origin Stage's Allowed Users"),
            ('domain', 'Custom Filter'),
        ],
        string='Who May Trigger Manually',
        default='any',
        required=True,
    )
    user_domain = fields.Char(
        string='Allowed Users Filter',
        default='[]',
        help='Only used when "Who May Trigger Manually" is set to Custom Filter.',
    )
    res_users_model = fields.Char(default='res.users')

    @api.depends('direction', 'to_stage_id', 'name')
    def _compute_display_name(self):
        for transition in self:
            arrow = '→' if transition.direction == 'forward' else '←'
            to_name = transition.to_stage_id.name or _('?')
            transition.display_name = '%s %s (%s)' % (arrow, to_name, transition.name)

    # ------------------------------------------------------------------ #
    # Availability checks                                                  #
    # ------------------------------------------------------------------ #

    def _get_eval_context(self, record=None):
        self.ensure_one()
        ctx = {
            'env': self.env,
            'user': self.env.user,
            'uid': self.env.uid,
        }
        if record is not None:
            ctx['record'] = record
        return ctx

    def _check_record_condition(self, record):
        """Return True if `record` satisfies this transition's record condition."""
        self.ensure_one()
        ctype = self.record_condition_type
        if ctype == 'none' or not ctype or record is None:
            return True

        eval_ctx = self._get_eval_context(record)

        if ctype == 'domain':
            try:
                domain = safe_eval.safe_eval(self.record_condition_domain or '[]', eval_ctx)
                return bool(record.filtered_domain(domain))
            except Exception:
                _logger.exception(
                    "wkf.transition '%s' — error evaluating record condition domain", self.name,
                )
                return False

        if ctype == 'python':
            try:
                return bool(safe_eval.safe_eval(self.record_condition_python or 'False', eval_ctx))
            except Exception:
                _logger.exception(
                    "wkf.transition '%s' — error evaluating record condition python", self.name,
                )
                return False

        return True

    def _check_user_allowed(self, user):
        """Return True if `user` is allowed to manually trigger this transition."""
        self.ensure_one()
        rtype = self.user_restriction_type or 'any'
        if rtype == 'any' or not user:
            return True

        if rtype == 'stage_users':
            domain_str = self.from_stage_id.user_domain or '[]'
        elif rtype == 'domain':
            domain_str = self.user_domain or '[]'
        else:
            return True

        try:
            domain = safe_eval.safe_eval(domain_str)
        except Exception:
            _logger.exception(
                "wkf.transition '%s' — error evaluating user filter", self.name,
            )
            return False

        if not domain:
            # An empty filter means "no restriction" — any user is allowed.
            return True
        return bool(self.env['res.users'].search_count(domain + [('id', '=', user.id)]))

    def is_available(self, record=None, user=None, manual=True):
        """Return True if this transition may be applied right now.

        Args:
            record: the record being transitioned (for the record condition).
            user: the user attempting a manual trigger. Ignored when manual=False.
            manual: True for a user-initiated change, False for a
                programmatic / automation-triggered change.
        """
        self.ensure_one()
        if manual and not self.allow_manual:
            return False
        if not manual and not self.allow_automatic:
            return False
        if not self._check_record_condition(record):
            return False
        if manual and not self._check_user_allowed(user):
            return False
        return True

# Part of Cliffs. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestWkfWorkflow(TransactionCase):
    """Core structural tests for the workflow / stage / transition graph.

    Mixin behaviour (create/write hooks on a consuming model) is exercised
    by whatever module actually inherits `wkf.stage.mixin` — there is no
    such model in this module to test against directly.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.model_category = cls.env['ir.model']._get('res.partner.category')
        cls.workflow = cls.env['wkf.workflow'].create({
            'name': 'Test Approval Workflow',
            'model_id': cls.model_category.id,
        })
        cls.stage_draft = cls.env['wkf.stage'].create({
            'workflow_id': cls.workflow.id,
            'name': 'Draft',
            'is_initial': True,
        })
        cls.stage_review = cls.env['wkf.stage'].create({
            'workflow_id': cls.workflow.id,
            'name': 'Review',
        })
        cls.stage_approved = cls.env['wkf.stage'].create({
            'workflow_id': cls.workflow.id,
            'name': 'Approved',
            'is_final': True,
        })
        cls.transition_submit = cls.env['wkf.transition'].create({
            'from_stage_id': cls.stage_draft.id,
            'to_stage_id': cls.stage_review.id,
            'name': 'Submit',
            'direction': 'forward',
        })
        cls.transition_approve = cls.env['wkf.transition'].create({
            'from_stage_id': cls.stage_review.id,
            'to_stage_id': cls.stage_approved.id,
            'name': 'Approve',
            'direction': 'forward',
        })
        cls.transition_reject = cls.env['wkf.transition'].create({
            'from_stage_id': cls.stage_review.id,
            'to_stage_id': cls.stage_draft.id,
            'name': 'Reject',
            'direction': 'backward',
        })

    def test_single_initial_stage_per_workflow(self):
        with self.assertRaises(ValidationError):
            self.env['wkf.stage'].create({
                'workflow_id': self.workflow.id,
                'name': 'Another Initial',
                'is_initial': True,
            })

    def test_unique_active_workflow_per_model(self):
        with self.assertRaises(ValidationError):
            self.env['wkf.workflow'].create({
                'name': 'Duplicate Workflow',
                'model_id': self.model_category.id,
            })
        # Archiving the original frees up the model for a new workflow.
        self.workflow.active = False
        second = self.env['wkf.workflow'].create({
            'name': 'Replacement Workflow',
            'model_id': self.model_category.id,
        })
        self.assertTrue(second)

    def test_multiple_transitions_from_same_stage(self):
        outgoing = self.stage_review.out_transition_ids
        self.assertEqual(len(outgoing), 2)
        self.assertEqual(set(outgoing.mapped('direction')), {'forward', 'backward'})

    def test_record_condition_domain(self):
        record = self.env['res.partner.category'].create({'name': 'Alpha'})
        self.transition_submit.write({
            'record_condition_type': 'domain',
            'record_condition_domain': "[('name', '=', 'Alpha')]",
        })
        self.assertTrue(self.transition_submit._check_record_condition(record))

        other = self.env['res.partner.category'].create({'name': 'Beta'})
        self.assertFalse(self.transition_submit._check_record_condition(other))

    def test_record_condition_python(self):
        record = self.env['res.partner.category'].create({'name': 'Alpha'})
        self.transition_submit.write({
            'record_condition_type': 'python',
            'record_condition_python': "record.name == 'Alpha'",
        })
        self.assertTrue(self.transition_submit._check_record_condition(record))
        self.transition_submit.write({'record_condition_python': "record.name == 'Nope'"})
        self.assertFalse(self.transition_submit._check_record_condition(record))

    def test_allow_manual_and_automatic_gating(self):
        self.transition_submit.write({'allow_manual': False, 'allow_automatic': True})
        self.assertFalse(self.transition_submit.is_available(manual=True))
        self.assertTrue(self.transition_submit.is_available(manual=False))

        self.transition_submit.write({'allow_manual': True, 'allow_automatic': False})
        self.assertTrue(self.transition_submit.is_available(manual=True))
        self.assertFalse(self.transition_submit.is_available(manual=False))

    def test_user_restriction_domain(self):
        restricted_user = self.env['res.users'].create({
            'name': 'Restricted Approver',
            'login': 'wkf_restricted_approver',
            'email': 'wkf_restricted_approver@example.com',
        })
        other_user = self.env['res.users'].create({
            'name': 'Someone Else',
            'login': 'wkf_someone_else',
            'email': 'wkf_someone_else@example.com',
        })
        self.transition_approve.write({
            'user_restriction_type': 'domain',
            'user_domain': "[('login', '=', 'wkf_restricted_approver')]",
        })
        self.assertTrue(self.transition_approve._check_user_allowed(restricted_user))
        self.assertFalse(self.transition_approve._check_user_allowed(other_user))

    def test_user_restriction_stage_users(self):
        allowed_user = self.env['res.users'].create({
            'name': 'Stage Allowed',
            'login': 'wkf_stage_allowed',
            'email': 'wkf_stage_allowed@example.com',
        })
        other_user = self.env['res.users'].create({
            'name': 'Not Stage Allowed',
            'login': 'wkf_stage_not_allowed',
            'email': 'wkf_stage_not_allowed@example.com',
        })
        self.stage_review.write({
            'user_domain': "[('login', '=', 'wkf_stage_allowed')]",
        })
        self.transition_approve.write({'user_restriction_type': 'stage_users'})
        self.assertTrue(self.transition_approve._check_user_allowed(allowed_user))
        self.assertFalse(self.transition_approve._check_user_allowed(other_user))

    def test_empty_domain_means_no_restriction(self):
        user = self.env['res.users'].create({
            'name': 'Anyone',
            'login': 'wkf_anyone',
            'email': 'wkf_anyone@example.com',
        })
        self.transition_approve.write({'user_restriction_type': 'domain', 'user_domain': '[]'})
        self.assertTrue(self.transition_approve._check_user_allowed(user))

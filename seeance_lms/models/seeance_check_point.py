from odoo import fields, models


class SeeanceCheckPoint(models.Model):
    _inherit = 'seeance.check_point'

    required_course_ids = fields.Many2many(
        'lms.course', string='Required Courses',
        help='Courses a worker must have completed before signing in at this Check Point.')

    def _get_pwa_features(self):
        self.ensure_one()
        features = super()._get_pwa_features()
        features['courses'] = True
        return features

    def _get_pwa_sync_payload(self):
        self.ensure_one()
        payload = super()._get_pwa_sync_payload()
        courses = self.env['lms.course'].sudo().search([])
        payload['courses'] = [{'id': c.id, 'name': c.name} for c in courses]
        payload['check_point']['required_course_ids'] = self.required_course_ids.ids
        return payload

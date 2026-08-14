from odoo import models


class SeeanceCheckPoint(models.Model):
    _inherit = 'seeance.check_point'

    def _get_pwa_identity_field(self):
        self.ensure_one()
        return 'employee_id'

    def _get_pwa_features(self):
        self.ensure_one()
        features = super()._get_pwa_features()
        features['employees'] = True
        return features

    def _get_pwa_sync_payload(self):
        self.ensure_one()
        payload = super()._get_pwa_sync_payload()
        employees = self.env['hr.employee'].sudo().search([
            ('company_id', '=', self.company_id.id), ('active', '=', True)])
        payload['employees'] = [
            {'id': e.id, 'name': e.name, 'user_id': e.user_id.id,
             'badge_code': e.seeance_badge_code}
            for e in employees
        ]
        return payload

    def _identify_person_by_pin(self, pin_code):
        self.ensure_one()
        employee = self.env['hr.employee'].sudo().search([
            ('seeance_identification_pin', '=', pin_code),
            ('company_id', '=', self.company_id.id),
            ('active', '=', True),
        ], limit=1)
        return {'id': employee.id, 'name': employee.name} if employee else None

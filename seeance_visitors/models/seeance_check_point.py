from datetime import timedelta

from odoo import api, fields, models


class SeeanceCheckPoint(models.Model):
    _inherit = 'seeance.check_point'

    allow_visitor_registration = fields.Boolean(
        string='Allow Visitor Registration',
        help='Allow visitors (non-employees) to register themselves in at this Check Point.')
    visitor_question_ids = fields.One2many(
        'seeance.visitor.question', 'check_point_id', string='Visitor Questions')
    visitor_registration_ids = fields.One2many(
        'seeance.visitor.registration', 'check_point_id', string='Visitor Registrations')
    visitor_registration_count = fields.Integer(compute='_compute_visitor_registration_count')

    visitor_registration_count_today = fields.Integer(
        string='Visitors Today', compute='_compute_visitor_stats')
    visitor_registration_count_wtd = fields.Integer(
        string='Visitors WTD', compute='_compute_visitor_stats')
    visitor_registration_count_mtd = fields.Integer(
        string='Visitors MTD', compute='_compute_visitor_stats')
    visitor_registration_count_ytd = fields.Integer(
        string='Visitors YTD', compute='_compute_visitor_stats')

    def _compute_visitor_registration_count(self):
        groups = self.env['seeance.visitor.registration']._read_group(
            [('check_point_id', 'in', self.ids)],
            groupby=['check_point_id'], aggregates=['__count'])
        count_map = {check_point.id: count for check_point, count in groups}
        for check_point in self:
            check_point.visitor_registration_count = count_map.get(check_point.id, 0)

    @api.depends('visitor_registration_ids.datetime')
    def _compute_visitor_stats(self):
        Registration = self.env['seeance.visitor.registration']
        today = fields.Date.context_today(self)
        periods = {
            'today': today,
            'wtd': today - timedelta(days=today.weekday()),
            'mtd': today.replace(day=1),
            'ytd': today.replace(month=1, day=1),
        }
        counts = {check_point.id: {} for check_point in self}
        for period, start_date in periods.items():
            start_utc = self._local_midnight_to_utc(start_date)
            groups = Registration._read_group(
                [('check_point_id', 'in', self.ids), ('datetime', '>=', start_utc)],
                groupby=['check_point_id'], aggregates=['__count'])
            for check_point, count in groups:
                counts[check_point.id][period] = count
        for check_point in self:
            values = counts.get(check_point.id, {})
            check_point.visitor_registration_count_today = values.get('today', 0)
            check_point.visitor_registration_count_wtd = values.get('wtd', 0)
            check_point.visitor_registration_count_mtd = values.get('mtd', 0)
            check_point.visitor_registration_count_ytd = values.get('ytd', 0)

    def action_view_visitor_registrations(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'seeance_visitors.seeance_visitor_registration_action')
        action['domain'] = [('check_point_id', '=', self.id)]
        return action

    def _get_pwa_features(self):
        self.ensure_one()
        features = super()._get_pwa_features()
        features['visitor_registration'] = self.allow_visitor_registration
        return features

    def _get_pwa_sync_payload(self):
        self.ensure_one()
        payload = super()._get_pwa_sync_payload()
        payload['check_point']['allow_visitor_registration'] = self.allow_visitor_registration
        if self.allow_visitor_registration:
            payload['visitor_questions'] = [
                {'id': q.id, 'name': q.name, 'sequence': q.sequence, 'is_required': q.is_required}
                for q in self.visitor_question_ids
            ]
        return payload

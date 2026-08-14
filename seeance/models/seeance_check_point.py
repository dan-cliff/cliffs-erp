import secrets
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models

# Minutes of silence after which a Check Point is considered offline / critically offline.
CONNECTIVITY_WARNING_AFTER_MINUTES = 5
CONNECTIVITY_DANGER_AFTER_MINUTES = 180


class SeeanceCheckPoint(models.Model):
    _name = 'seeance.check_point'
    _description = 'Seeance Check Point'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    work_location_id = fields.Many2one(
        'seeance.work_location', string='Work Location', required=True,
        domain="[('company_id', '=', company_id)]",
        help='The work location workers sign in to at this Check Point.')
    capture_photo = fields.Boolean(
        string='Capture Photo',
        help="Take the person's photo while they sign in and/or out at this Check Point.")
    attendance_ids = fields.One2many(
        'seeance.attendance', 'check_point_id', string='Sign In/Out Records')

    # Kiosk / PWA provisioning
    access_pin = fields.Char(
        string='Kiosk PIN', copy=False, readonly=True,
        default=lambda self: secrets.token_hex(8))
    kiosk_url = fields.Char(string='Kiosk URL', compute='_compute_kiosk_url')
    kiosk_qr_code = fields.Binary(string='Kiosk QR Code', compute='_compute_kiosk_qr_code')

    # Heartbeat / connectivity, reported by the PWA on every sync/heartbeat call.
    last_seen = fields.Datetime(string='Last Seen', readonly=True, copy=False)
    last_ip = fields.Char(string='Last IP Address', readonly=True, copy=False)
    last_os_info = fields.Char(string='Last Device Info', readonly=True, copy=False)
    last_connection_type = fields.Char(string='Last Connection Type', readonly=True, copy=False)
    connectivity_status = fields.Selection(
        [('never', 'Never Connected'),
         ('online', 'Online'),
         ('warning', 'Offline'),
         ('danger', 'Offline 3h+')],
        string='Connectivity', compute='_compute_connectivity_status')

    _sql_constraints = [
        ('access_pin_uniq', 'unique(access_pin)',
         'Each Check Point must have a unique kiosk PIN.'),
    ]

    # Statistics
    sign_in_count_today = fields.Integer(string='Sign Ins Today', compute='_compute_attendance_stats')
    sign_in_count_wtd = fields.Integer(string='Sign Ins WTD', compute='_compute_attendance_stats')
    sign_in_count_mtd = fields.Integer(string='Sign Ins MTD', compute='_compute_attendance_stats')
    sign_in_count_ytd = fields.Integer(string='Sign Ins YTD', compute='_compute_attendance_stats')
    sign_out_count_today = fields.Integer(string='Sign Outs Today', compute='_compute_attendance_stats')
    sign_out_count_wtd = fields.Integer(string='Sign Outs WTD', compute='_compute_attendance_stats')
    sign_out_count_mtd = fields.Integer(string='Sign Outs MTD', compute='_compute_attendance_stats')
    sign_out_count_ytd = fields.Integer(string='Sign Outs YTD', compute='_compute_attendance_stats')

    @api.depends('last_seen')
    def _compute_connectivity_status(self):
        now = fields.Datetime.now()
        for check_point in self:
            if not check_point.last_seen:
                check_point.connectivity_status = 'never'
                continue
            minutes = (now - check_point.last_seen).total_seconds() / 60
            if minutes <= CONNECTIVITY_WARNING_AFTER_MINUTES:
                check_point.connectivity_status = 'online'
            elif minutes <= CONNECTIVITY_DANGER_AFTER_MINUTES:
                check_point.connectivity_status = 'warning'
            else:
                check_point.connectivity_status = 'danger'

    def _compute_kiosk_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or ''
        for check_point in self:
            check_point.kiosk_url = (
                f'{base_url}/seeance/kiosk/{check_point.id}?pin={check_point.access_pin}'
                if check_point.id else False)

    def _compute_kiosk_qr_code(self):
        for check_point in self:
            if not check_point.kiosk_url:
                check_point.kiosk_qr_code = False
                continue
            try:
                check_point.kiosk_qr_code = self.env['ir.actions.report'].barcode(
                    barcode_type='QR', value=check_point.kiosk_url, width=256, height=256)
            except Exception:
                check_point.kiosk_qr_code = False

    def _local_midnight_to_utc(self, date):
        tz = pytz.timezone(self.env.user.tz or 'UTC')
        local_dt = tz.localize(datetime.combine(date, time.min))
        return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)

    @api.depends('attendance_ids.mechanism', 'attendance_ids.datetime')
    def _compute_attendance_stats(self):
        Attendance = self.env['seeance.attendance']
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
            groups = Attendance._read_group(
                [('check_point_id', 'in', self.ids), ('datetime', '>=', start_utc)],
                groupby=['check_point_id', 'mechanism'],
                aggregates=['__count'])
            for check_point, mechanism, count in groups:
                counts[check_point.id][(period, mechanism)] = count
        for check_point in self:
            values = counts.get(check_point.id, {})
            check_point.sign_in_count_today = values.get(('today', 'sign_in'), 0)
            check_point.sign_in_count_wtd = values.get(('wtd', 'sign_in'), 0)
            check_point.sign_in_count_mtd = values.get(('mtd', 'sign_in'), 0)
            check_point.sign_in_count_ytd = values.get(('ytd', 'sign_in'), 0)
            check_point.sign_out_count_today = values.get(('today', 'sign_out'), 0)
            check_point.sign_out_count_wtd = values.get(('wtd', 'sign_out'), 0)
            check_point.sign_out_count_mtd = values.get(('mtd', 'sign_out'), 0)
            check_point.sign_out_count_ytd = values.get(('ytd', 'sign_out'), 0)

    attendance_count = fields.Integer(compute='_compute_attendance_count')

    def _compute_attendance_count(self):
        groups = self.env['seeance.attendance']._read_group(
            [('check_point_id', 'in', self.ids)],
            groupby=['check_point_id'], aggregates=['__count'])
        count_map = {check_point.id: count for check_point, count in groups}
        for check_point in self:
            check_point.attendance_count = count_map.get(check_point.id, 0)

    def action_view_attendances(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('seeance.seeance_attendance_action')
        action['domain'] = [('check_point_id', '=', self.id)]
        action['context'] = {'default_check_point_id': self.id}
        return action

    def action_regenerate_access_pin(self):
        for check_point in self:
            check_point.access_pin = secrets.token_hex(8)

    # -- PWA extension hooks -------------------------------------------------
    # Optional add-on modules (seeance_hr, seeance_lms, seeance_visitors) override
    # these to plug their own data into the kiosk's offline sync payload, without
    # this module ever needing to know whether they are installed.

    def _get_pwa_identity_field(self):
        """Name of the field on seeance.attendance used to record who signed in/out."""
        self.ensure_one()
        return 'user_id'

    def _get_pwa_features(self):
        self.ensure_one()
        return {
            'employees': False,
            'courses': False,
            'visitor_registration': False,
        }

    def _get_pwa_sync_payload(self):
        self.ensure_one()
        users = self.env['res.users'].sudo().search([
            ('company_ids', 'in', [self.company_id.id]), ('active', '=', True)])
        work_locations = self.env['seeance.work_location'].sudo().search([
            ('company_id', '=', self.company_id.id)])
        return {
            'check_point': {
                'id': self.id,
                'name': self.name,
                'company_id': self.company_id.id,
                'company_name': self.company_id.name,
                'work_location_id': self.work_location_id.id,
                'work_location_name': self.work_location_id.name,
                'capture_photo': self.capture_photo,
            },
            'identity_field': self._get_pwa_identity_field(),
            'features': self._get_pwa_features(),
            'users': [{'id': u.id, 'name': u.name, 'login': u.login} for u in users],
            'work_locations': [{'id': w.id, 'name': w.name} for w in work_locations],
            'server_time': fields.Datetime.to_string(fields.Datetime.now()),
        }

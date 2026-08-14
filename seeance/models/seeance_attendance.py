from odoo import api, fields, models


class SeeanceAttendance(models.Model):
    _name = 'seeance.attendance'
    _description = 'Seeance Sign In/Out Record'
    _order = 'datetime desc'

    datetime = fields.Datetime(
        required=True, default=fields.Datetime.now, readonly=True)
    mechanism = fields.Selection(
        [('sign_in', 'Sign In'), ('sign_out', 'Sign Out')],
        required=True, readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    work_location_id = fields.Many2one(
        'seeance.work_location', string='Work Location', required=True, readonly=True)
    check_point_id = fields.Many2one(
        'seeance.check_point', string='Check Point', required=True, readonly=True)
    user_id = fields.Many2one(
        'res.users', string='User', readonly=True,
        help='Who signed in/out. Used when the Employees app is not installed.')
    image = fields.Image(
        string='Photo', max_width=1024, max_height=1024, attachment=True)
    origin_uuid = fields.Char(
        string='Origin UUID', copy=False, readonly=True,
        help='Client-generated identifier used to make offline kiosk submissions idempotent.')

    _sql_constraints = [
        ('origin_uuid_uniq', 'unique(origin_uuid)',
         'This sign in/out record has already been recorded.'),
    ]

    @api.onchange('check_point_id')
    def _onchange_check_point_id(self):
        for record in self:
            if record.check_point_id:
                record.company_id = record.check_point_id.company_id
                record.work_location_id = record.check_point_id.work_location_id

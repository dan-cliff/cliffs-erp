from odoo import fields, models


class SeeanceCheckPoint(models.Model):
    _inherit = 'seeance.check_point'

    required_course_ids = fields.Many2many(
        'lms.course', string='Required Courses',
        help='Courses a worker must have completed before signing in at this Check Point.')

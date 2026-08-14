from odoo import fields, models


class SeeanceVisitorRegistration(models.Model):
    _name = 'seeance.visitor.registration'
    _description = 'Seeance Visitor Registration'
    _order = 'datetime desc'

    name = fields.Char(string='Visitor Name', required=True, readonly=True)
    datetime = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, readonly=True,
        default=lambda self: self.env.company)
    work_location_id = fields.Many2one(
        'seeance.work_location', string='Work Location', required=True, readonly=True)
    check_point_id = fields.Many2one(
        'seeance.check_point', string='Check Point', required=True, readonly=True)
    image = fields.Image(
        string='Photo', max_width=1024, max_height=1024, attachment=True)
    answer_ids = fields.One2many(
        'seeance.visitor.registration.answer', 'registration_id', string='Answers')
    origin_uuid = fields.Char(
        string='Origin UUID', copy=False, readonly=True,
        help='Client-generated identifier used to make offline kiosk submissions idempotent.')

    _sql_constraints = [
        ('origin_uuid_uniq', 'unique(origin_uuid)',
         'This visitor registration has already been recorded.'),
    ]


class SeeanceVisitorRegistrationAnswer(models.Model):
    _name = 'seeance.visitor.registration.answer'
    _description = 'Seeance Visitor Registration Answer'
    _order = 'question_id'

    registration_id = fields.Many2one(
        'seeance.visitor.registration', string='Registration',
        required=True, ondelete='cascade')
    question_id = fields.Many2one(
        'seeance.visitor.question', string='Question', required=True, readonly=True)
    answer = fields.Text(readonly=True)

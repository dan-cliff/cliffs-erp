from odoo import api, fields, models


class SeeanceAttendance(models.Model):
    _inherit = 'seeance.attendance'

    employee_id = fields.Many2one('hr.employee', string='Employee', readonly=True)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.user_id = record.employee_id.user_id

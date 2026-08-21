from odoo import fields, models


class DevOpsSprint(models.Model):
    _name = 'dev.ops.sprint'
    _description = 'Sprint'
    _order = 'start_date desc, name'

    name = fields.Char(required=True)
    description = fields.Text()
    status = fields.Selection([
        ('planning', 'Planning'),
        ('in_progress', 'In Progress'),
        ('testing', 'Testing'),
        ('released', 'Released'),
        ('cancelled', 'Cancelled'),
    ], default='planning', required=True, tracking=False)
    icon = fields.Image(max_width=256, max_height=256)
    trivia = fields.Text()
    release_notes = fields.Html(sanitize=True)
    start_date = fields.Date()
    end_date = fields.Date()
    release_date_alpha = fields.Date(string='Release Date (Alpha)')
    release_date_beta = fields.Date(string='Release Date (Beta)')
    release_date_general = fields.Date(string='Release Date (General)')
    release_candidate_id = fields.Many2one(
        'dev.ops.release.candidate', string='Release Candidates')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A sprint with this name already exists.'),
    ]

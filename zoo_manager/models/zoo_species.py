from odoo import api, fields, models


class ZooSpecies(models.Model):
    _name = 'zoo.species'
    _description = 'Species'
    _inherit = ['zoo.prefix.code.mixin']
    _order = 'name'

    _prefix_code_length = 3

    name = fields.Char(string='Common Name', required=True)
    scientific_name = fields.Char()
    class_id = fields.Many2one('zoo.animal.class', string='Class', index=True)
    species_code = fields.Char(
        index=True,
        help='Regulatory species code used on the annual wildlife return.',
    )
    include_on_annual_return = fields.Boolean(
        string='Include on Annual Wildlife Return',
        help='Should this Species be included on the annual wildlife return?',
    )
    conservation_status = fields.Selection(
        [
            ('ne', 'Not Evaluated'),
            ('dd', 'Data Deficient'),
            ('lc', 'Least Concern'),
            ('nt', 'Near Threatened'),
            ('vu', 'Vulnerable'),
            ('en', 'Endangered'),
            ('cr', 'Critically Endangered'),
            ('ew', 'Extinct in the Wild'),
        ],
        string='Conservation Status (IUCN)',
    )
    default_diet_id = fields.Many2one(
        'zoo.diet',
        string='Default Diet',
        help='Diet given to new animals of this species.',
    )
    description = fields.Html()
    animal_ids = fields.One2many('zoo.animal', 'species_id', string='Animals')
    animal_count = fields.Integer(compute='_compute_animal_count')
    active = fields.Boolean(default=True)

    _name_uniq = models.Constraint('UNIQUE (name)', 'A species with this name already exists.')
    _prefix_code_uniq = models.Constraint('UNIQUE (prefix_code)', 'Another species already uses this Prefix Code.')

    @api.depends('animal_ids')
    def _compute_animal_count(self):
        counts = dict(self.env['zoo.animal']._read_group(
            [('species_id', 'in', self.ids)], ['species_id'], ['__count'],
        ))
        for species in self:
            species.animal_count = counts.get(species, 0)

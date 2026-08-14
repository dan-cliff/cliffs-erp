from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResUsers(models.Model):
    _inherit = 'res.users'

    seeance_identification_pin = fields.Char(
        string='Seeance Kiosk PIN',
        help='Personal PIN used to identify this person at a Seeance Check Point kiosk '
             '(PIN identification method). Kept server-side only, never synced to kiosks.')
    seeance_badge_code = fields.Char(
        string='Seeance Badge Code',
        help="The value encoded on this person's ID card (QR code payload or RFID tag), used "
             'to identify them at a Seeance Check Point kiosk via QR/RFID scanning.')

    _sql_constraints = [
        ('seeance_identification_pin_uniq', 'unique(seeance_identification_pin)',
         'This PIN is already used by another person.'),
        ('seeance_badge_code_uniq', 'unique(seeance_badge_code)',
         'This badge code is already assigned to another person.'),
    ]

    @api.constrains('seeance_identification_pin')
    def _check_seeance_identification_pin(self):
        for user in self:
            pin = user.seeance_identification_pin
            if pin and not (pin.isdigit() and 4 <= len(pin) <= 8):
                raise ValidationError('The Seeance Kiosk PIN must be 4 to 8 digits.')

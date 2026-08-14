from odoo import api, fields, models
from odoo.addons.base.models.res_partner import _tz_get


class AimsInstance(models.Model):
    _name = 'aims.instance'
    _description = 'AIMS Instance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Instance Name', required=True, tracking=True)
    url = fields.Char(string='URL')
    active = fields.Boolean(default=True)

    server_id = fields.Many2one(
        'aims.server', string='Server', required=True, tracking=True)
    cloud_provider_id = fields.Many2one(
        'aims.cloud.provider', string='Cloud Provider',
        related='server_id.cloud_provider_id', store=True, readonly=True)

    subscription_id = fields.Many2one(
        'sale.subscription', string='Subscription', tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
        domain=[('is_company', '=', True)], tracking=True)

    account_status_id = fields.Many2one(
        'aims.account.status', string='Account Status', tracking=True)
    account_health_id = fields.Many2one(
        'aims.account.health', string='Account Health', tracking=True)
    account_package_id = fields.Many2one(
        'aims.account.package', string='Account Package', tracking=True)
    instance_type_id = fields.Many2one(
        'aims.instance.type', string='Type', tracking=True)

    tz = fields.Selection(_tz_get, string='Primary Timezone')
    last_backup = fields.Datetime(string='Last Backup')
    active_user_count = fields.Integer(string='Active User Count')
    licenced_user_count = fields.Integer(string='Licenced User Count')
    version = fields.Char(string='Version')

    # Features
    feature_sms_enabled = fields.Boolean(
        string='Enable SMS',
        help=(
            "Allows integration to the CSS SMS gateway, note this comes at an "
            "additional charge and should be included in the subscription plan "
            "before activating. Where special allowances are being made, this "
            "should be included in the clients contact and SMS still be enabled "
            "on the subscription, but at a discounted rate."
        ),
    )

    @api.onchange('subscription_id')
    def _onchange_subscription_id(self):
        for instance in self:
            if instance.subscription_id.partner_id:
                instance.partner_id = instance.subscription_id.partner_id

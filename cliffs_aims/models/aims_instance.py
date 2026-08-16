import hashlib
import hmac
import logging
import secrets
import time
import xmlrpc.client

from odoo import _, api, fields, models
from odoo.addons.base.models.res_partner import _tz_get
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)

SYSTEM_MANAGER_LOGIN_DEFAULT = 'system.manager@cliffs.internal'
LOGIN_TOKEN_TTL = 120
LOGIN_ROUTE_PATH = '/cliffs/system_login/'


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
    active_user_count_updated = fields.Datetime(string='Active User Count Last Synced', readonly=True)
    licenced_user_count = fields.Integer(string='Licenced User Count')
    version = fields.Char(string='Version')

    # System Manager access - used for the "log in as" button and the
    # nightly active-user-count sync. The instance's own database, over on
    # its own Cloudpepper-managed server, is what actually holds this
    # account; these fields just store what AIMS needs to reach it.
    database_name = fields.Char(
        string='Database Name',
        help="Odoo database name on the client instance, used for API access. "
             "Leave blank if the instance resolves its database automatically "
             "from the domain.")
    system_manager_login = fields.Char(
        string='System Manager Login', default=SYSTEM_MANAGER_LOGIN_DEFAULT)
    system_manager_api_key = fields.Char(
        string='System Manager API Key', groups='cliffs_aims.group_instance_credentials')
    system_manager_token_secret = fields.Char(
        string='System Manager Login Token Secret', groups='cliffs_aims.group_instance_credentials')

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

    def write(self, vals):
        # url/database_name/system_manager_login decide where the stored
        # API key gets sent by the sync cron. They're ordinary editable
        # fields on instances with no credential yet, but once a key is
        # set, changing them is equivalent to redirecting that credential
        # to a different host - restrict that specifically, without
        # locking the URL field down for everyone.
        redirect_fields = {'url', 'database_name', 'system_manager_login'}
        if redirect_fields & vals.keys() and not self.env.user.has_group(
                'cliffs_aims.group_instance_credentials'):
            # sudo(): the acting user may lack read access to the credential
            # field itself (that's the point of the group restriction) - the
            # existence check below must not depend on their own visibility
            # into it, or it would silently never trigger for them.
            for instance in self.sudo():
                if instance.system_manager_api_key:
                    raise AccessError(_(
                        "Only members of AIMS / Instance Credentials can change the "
                        "URL, database name or System Manager login on an instance "
                        "that already has a System Manager API key set."))
        return super().write(vals)

    def action_login_as_system_manager(self):
        self.ensure_one()
        if not self.url:
            raise UserError(_('Set the instance URL before logging in as System Manager.'))
        if not self.system_manager_token_secret:
            raise UserError(_('Set the System Manager login token secret before logging in.'))

        token = self._make_login_token(self.system_manager_token_secret)
        return {
            'type': 'ir.actions.act_url',
            'url': f'{self.url.rstrip("/")}{LOGIN_ROUTE_PATH}{token}',
            'target': 'new',
        }

    @staticmethod
    def _make_login_token(secret, ttl=LOGIN_TOKEN_TTL):
        nonce = secrets.token_urlsafe(16)
        expires_at = int(time.time()) + ttl
        message = f'{nonce}.{expires_at}'.encode()
        signature = hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
        return f'{nonce}.{expires_at}.{signature}'

    def _cron_sync_active_user_counts(self):
        instances = self.search([
            ('url', '!=', False),
            ('system_manager_api_key', '!=', False),
        ])
        for instance in instances:
            try:
                instance._sync_active_user_count()
            except Exception:
                _logger.exception(
                    "AIMS: failed to sync active user count for instance %r", instance.name)

    def _sync_active_user_count(self):
        self.ensure_one()
        base_url = self.url.rstrip('/')
        db = self.database_name or ''
        login = self.system_manager_login or SYSTEM_MANAGER_LOGIN_DEFAULT

        common = xmlrpc.client.ServerProxy(f'{base_url}/xmlrpc/2/common')
        uid = common.authenticate(db, login, self.system_manager_api_key, {})
        if not uid:
            raise UserError(_('Authentication to %s failed.') % base_url)

        models_proxy = xmlrpc.client.ServerProxy(f'{base_url}/xmlrpc/2/object')
        count = models_proxy.execute_kw(
            db, uid, self.system_manager_api_key,
            'res.users', 'search_count', [[('share', '=', False), ('active', '=', True)]],
        )
        self.write({
            'active_user_count': count,
            'active_user_count_updated': fields.Datetime.now(),
        })

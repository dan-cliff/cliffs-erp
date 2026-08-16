import logging
import secrets

from .const import (
    API_KEY_SCOPE,
    SYSTEM_MANAGER_LOGIN,
    SYSTEM_MANAGER_XML_ID,
    TOKEN_SECRET_PARAM,
)

_logger = logging.getLogger(__name__)

HIDE_RULE_NAME = 'Hide Cliffs System Manager from all non-technical access'


def create_system_manager(env):
    """Idempotently provision the hidden System Manager account.

    Runs on every module install/update. Only ever generates new secrets
    the first time each piece is missing, so re-running (e.g. on a module
    upgrade) never rotates credentials AIMS already has stored.
    """
    users = env['res.users'].sudo()
    module, name = SYSTEM_MANAGER_XML_ID.split('.')

    user = env.ref(SYSTEM_MANAGER_XML_ID, raise_if_not_found=False)
    if not user:
        user = users.with_context(no_reset_password=True).create({
            'name': 'System Manager',
            'login': SYSTEM_MANAGER_LOGIN,
            'password': secrets.token_urlsafe(48),
            'groups_id': [(6, 0, [env.ref('base.group_system').id])],
            'company_ids': [(6, 0, env['res.company'].sudo().search([]).ids)],
        })
        env['ir.model.data'].sudo().create({
            'name': name,
            'module': module,
            'model': 'res.users',
            'res_id': user.id,
            'noupdate': True,
        })

    # A single global (all-groups) record rule keeps this account out of
    # every ordinary search/read/export - UI and external API alike - for
    # everyone except the real superuser. Nobody needs to see the row: the
    # login controller and the XML-RPC integration both reach it directly.
    if not env['ir.rule'].sudo().search([('name', '=', HIDE_RULE_NAME)]):
        env['ir.rule'].sudo().create({
            'name': HIDE_RULE_NAME,
            'model_id': env['ir.model']._get('res.users').id,
            'domain_force': "[('id', '!=', %d)]" % user.id,
        })

    secrets_generated = {}

    if not env['res.users.apikeys'].sudo().search([('user_id', '=', user.id)]):
        api_key = env['res.users.apikeys'].sudo().with_user(user)._generate(
            API_KEY_SCOPE, 'AIMS integration')
        secrets_generated['API key'] = api_key

    config = env['ir.config_parameter'].sudo()
    if not config.get_param(TOKEN_SECRET_PARAM):
        token_secret = secrets.token_urlsafe(32)
        config.set_param(TOKEN_SECRET_PARAM, token_secret)
        secrets_generated['Login token secret'] = token_secret

    if secrets_generated:
        _logger.warning(
            "Cliffs System Manager provisioned (res.users #%s). Copy the "
            "values below into the matching Instance record in AIMS now - "
            "they will not be shown again:\n%s",
            user.id,
            '\n'.join(f'  {key}: {value}' for key, value in secrets_generated.items()),
        )

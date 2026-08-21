import logging

import requests

from odoo import fields, models

_logger = logging.getLogger(__name__)

CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'
CLAUDE_API_VERSION = '2023-06-01'
# Small, cheap model used purely to confirm the key can authenticate.
CLAUDE_VALIDATION_MODEL = 'claude-haiku-4-5-20251001'
CLAUDE_VALIDATION_TIMEOUT = 15


class ResCompany(models.Model):
    _inherit = 'res.company'

    claude_api_key = fields.Char(string='Claude API Key')
    claude_api_key_error = fields.Boolean(
        string='Claude API Key Error', copy=False)
    claude_api_key_error_message = fields.Char(
        string='Claude API Key Error Message', copy=False)
    dev_ops_sprint_naming_prompt = fields.Text(string='Sprint Naming Prompt')

    def _cron_validate_claude_api_key(self):
        companies = self.sudo().search([('claude_api_key', '!=', False)])
        for company in companies:
            company._validate_claude_api_key()

    def _validate_claude_api_key(self):
        """Ping the Claude API with the configured key and update the
        error flag/message so it reflects the current state, clearing it
        again as soon as authentication succeeds.
        """
        self.ensure_one()
        try:
            response = requests.post(
                CLAUDE_API_URL,
                headers={
                    'x-api-key': self.claude_api_key,
                    'anthropic-version': CLAUDE_API_VERSION,
                    'content-type': 'application/json',
                },
                json={
                    'model': CLAUDE_VALIDATION_MODEL,
                    'max_tokens': 1,
                    'messages': [{'role': 'user', 'content': 'ping'}],
                },
                timeout=CLAUDE_VALIDATION_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            self._set_claude_api_key_error(str(exc))
            return

        if response.status_code == 200:
            self._clear_claude_api_key_error()
            return

        try:
            error_body = response.json().get('error', {})
        except ValueError:
            error_body = {}
        error_code = error_body.get('type') or str(response.status_code)
        error_detail = error_body.get('message') or response.text
        self._set_claude_api_key_error(f'{error_code}: {error_detail}')

    def _set_claude_api_key_error(self, error_message):
        self.ensure_one()
        _logger.error(
            'Claude API key validation failed for company %s: %s',
            self.name, error_message)
        self.write({
            'claude_api_key_error': True,
            'claude_api_key_error_message': error_message[:250],
        })

    def _clear_claude_api_key_error(self):
        self.ensure_one()
        if self.claude_api_key_error:
            self.write({
                'claude_api_key_error': False,
                'claude_api_key_error_message': False,
            })

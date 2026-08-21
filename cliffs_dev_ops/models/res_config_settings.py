from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    claude_api_key = fields.Char(
        related='company_id.claude_api_key', readonly=False)
    claude_api_key_error = fields.Boolean(
        related='company_id.claude_api_key_error')
    claude_api_key_error_message = fields.Char(
        related='company_id.claude_api_key_error_message')
    dev_ops_sprint_naming_prompt = fields.Text(
        related='company_id.dev_ops_sprint_naming_prompt', readonly=False)

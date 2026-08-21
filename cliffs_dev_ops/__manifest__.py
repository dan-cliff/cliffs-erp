{
    'name': 'Cliffs Dev Ops',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Sprint tracking, release management and Claude AI integration settings',
    'description': """
Dev Ops
=======
Adds a "Dev Ops" application for tracking Sprints and their Release
Candidates, plus a Claude AI integration:

* Sprints model with status, release notes, release-candidate tracking and
  Alpha/Beta/General release dates.
* A Configuration menu (always last in the app's menu bar) holding the
  Release Candidates it manages.
* A "Claude API Key" field on General Settings > Integrations, validated
  every night against the Anthropic API. Authentication failures are
  logged and flagged on the field until the key is valid again.
* A "Dev Ops" settings page for documenting the AI prompt used to name
  new sprints, shown once a Claude API Key is configured.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base', 'base_setup', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/dev_ops_sprint_views.xml',
        'views/dev_ops_release_candidate_views.xml',
        'views/dev_ops_menus.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

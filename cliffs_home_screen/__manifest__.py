{
    'name': 'Cliffs Home Screen',
    'version': '19.0.1.4.0',
    'category': 'Extra Tools',
    'summary': 'Custom home screen showing installed apps as an icon grid',
    'description': """
Replaces the default Odoo home screen with a custom one that lists every
installed app (top-level, non-archived menus with no Parent Menu) as an
icon grid, in the style of Odoo's standard app switcher. The top navbar's
app-switcher icon opens this home screen instead of its usual dropdown.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base', 'base_setup', 'web'],
    'data': [
        'data/home_screen_action.xml',
        'data/ir_config_parameter.xml',
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cliffs_home_screen/static/src/**/*',
        ],
    },
    'post_init_hook': '_set_home_screen_as_default_action',
    'uninstall_hook': '_unset_home_screen_as_default_action',
    'installable': True,
    'application': False,
    'auto_install': False,
}

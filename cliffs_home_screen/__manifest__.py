{
    'name': 'Cliffs Home Screen',
    'version': '19.0.1.0.0',
    'category': 'Extra Tools',
    'summary': 'Custom home screen listing installed apps with drill-down navigation',
    'description': """
Replaces the default Odoo home screen with a custom one that lists every
installed app (top-level, non-archived menus with no Parent Menu) and lets
users expand each app inline to browse its menu structure and jump straight
to a feature, without leaving the home screen.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base', 'web'],
    'data': [
        'data/home_screen_action.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cliffs_home_screen/static/src/home_screen/**/*',
        ],
    },
    'post_init_hook': '_set_home_screen_as_default_action',
    'uninstall_hook': '_unset_home_screen_as_default_action',
    'installable': True,
    'application': False,
    'auto_install': False,
}

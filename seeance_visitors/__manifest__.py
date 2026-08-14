{
    'name': 'Seeance - Visitor Registration',
    'version': '19.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Register visitors signing in at Seeance Check Points',
    'description': """
Seeance - Visitor Registration
===============================
Lets a Check Point allow visitors (non-employees) to register themselves
when signing in, and lets you configure the questions asked of them.

This module bridges Seeance and Contacts, so it only installs, and this
feature only appears, once both apps are installed.
""",
    'author': 'Cliffs',
    'license': 'LGPL-3',
    'depends': ['seeance', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/seeance_check_point_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
}
